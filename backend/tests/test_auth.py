from fastapi.testclient import TestClient


def test_valid_login_and_protected_route(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_invalid_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    assert client.get("/api/products").status_code == 401
