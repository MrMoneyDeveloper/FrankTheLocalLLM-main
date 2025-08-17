from ..app import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_status_endpoint():
    resp = client.get('/status')
    assert resp.status_code == 200
    assert resp.json() == {"llm_loaded": True, "docs_indexed": 342}
