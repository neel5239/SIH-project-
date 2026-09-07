from fastapi.testclient import TestClient
from services.m6_platform.main import app

def test_demo_token():
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/demo-token",
        json={"user_id": "doctor-1", "role": "physician"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
