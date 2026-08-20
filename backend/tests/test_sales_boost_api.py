from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_manual_add_list_and_duplicate_handling(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "title": "Wireless Neck Fan",
        "category": "Home & Kitchen",
        "keywords": ["Cooling", "portable fan"],
    }
    with patch("app.api.routes.sales_boost.rescore_all_products.delay") as delay:
        delay.return_value.id = "score-task"
        created = client.post("/api/sales-boost", json=payload, headers=auth_headers)
    assert created.status_code == 201
    assert created.json()["keywords"] == ["cooling", "portable fan"]
    assert created.json()["rescore_task_id"] == "score-task"

    listed = client.get("/api/sales-boost", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    duplicate = client.post("/api/sales-boost", json=payload, headers=auth_headers)
    assert duplicate.status_code == 409


def test_valid_csv_reports_invalid_and_duplicate_rows(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    csv_data = (
        b'title,category,keywords\n'
        b'Neck Fan,Home & Kitchen,"fan,cooling"\n'
        b'Neck Fan,Home & Kitchen,"duplicate"\n'
        b',Missing Title,"invalid"\n'
    )
    with patch("app.api.routes.sales_boost.rescore_all_products.delay") as delay:
        delay.return_value.id = "score-task"
        response = client.post(
            "/api/sales-boost/import",
            files={"file": ("history.csv", BytesIO(csv_data), "text/csv")},
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["duplicates"] == 1
    assert body["invalid_rows"] == [
        {"row": 4, "error": "Invalid title, category, or keywords"}
    ]


def test_invalid_csv_headers_are_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/sales-boost/import",
        files={"file": ("bad.csv", BytesIO(b"name,type\nA,B\n"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 422
