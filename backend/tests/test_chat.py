
def test_chat_endpoint(client, llm):
    resp = client.post("/api/chat/", json={"message": "hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "hello"
    assert not data["cached"]
