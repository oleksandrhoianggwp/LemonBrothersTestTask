from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_amazon_endpoint_enqueues_and_returns_202(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch("app.api.routes.scraping.run_amazon_collection.delay") as delay:
        delay.return_value = SimpleNamespace(id="amazon-task-id")
        response = client.post("/api/scraping/amazon", headers=auth_headers)
    assert response.status_code == 202
    assert response.json() == {"task_id": "amazon-task-id", "status": "PENDING"}
    delay.assert_called_once_with()
