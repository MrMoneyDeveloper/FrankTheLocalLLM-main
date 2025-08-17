from ..app import models


def test_create_entry(client):
    resp = client.post(
        "/api/entries/",
        json={"title": "test", "group": "grp", "content": "hello world"},
    )
    assert resp.status_code == 200
    entry_id = resp.json()["id"]

    resp = client.get("/api/entries/")
    assert resp.status_code == 200
    entries = resp.json()
    assert any(e["id"] == entry_id for e in entries)
