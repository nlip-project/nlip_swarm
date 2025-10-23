from fastapi.testclient import TestClient
from backend.app.api import app


def test_process_endpoint():
    client = TestClient(app)
    payload = {
        "schema": "nlip/v1",
        "id": "msg-1",
        "sender": "client",
        "messages": [
            {"format": "text", "content": "hello"}
        ]
    }

    resp = client.post("/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["schema"] == "nlip/v1"
    assert data["id"] == "msg-1"
    assert data["receiver"] == "client"
    assert data["messages"][0]["content"] == "hello"
    assert data["sender"] == "supervisor"
