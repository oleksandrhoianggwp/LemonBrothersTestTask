from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_trends_endpoint_enqueues_and_returns_202(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch("app.api.routes.trends.run_trend_collection.delay") as delay:
        delay.return_value = SimpleNamespace(id="trend-task-id")
        response = client.post("/api/trends/collect", headers=auth_headers)
    assert response.status_code == 202
    assert response.json() == {"task_id": "trend-task-id", "status": "PENDING"}
    delay.assert_called_once_with()
