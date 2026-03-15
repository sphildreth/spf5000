from fastapi.testclient import TestClient

from app.main import create_app


def test_health() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["app"] == "SPF5000"
