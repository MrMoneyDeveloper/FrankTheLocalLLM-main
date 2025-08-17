from ..app.security import get_password_hash
from ..app import models


def test_register_and_login(client):
    resp = client.post("/api/auth/register", json={"username": "test", "password": "pw"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "test"
    assert "id" in data

    resp = client.post("/api/auth/login", json={"username": "test", "password": "pw"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    resp = client.get("/api/user/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "test"
