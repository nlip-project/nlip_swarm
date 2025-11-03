from fastapi.testclient import TestClient

from backend.app import supervisor
from backend.app.api import setup_server


class DummyTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, text: str, target_locale: str) -> str:
        self.calls.append((text, target_locale))
        if target_locale == "en":
            return "the crop looks healthy"
        if target_locale == "lg":
            assert text == "the crop looks healthy"
            return "ebirime birabika bulungi"
        return text

"""
def test_process_endpoint_translates_through_pivot(monkeypatch):
    client = TestClient(app)
    dummy_translator = DummyTranslator()
    monkeypatch.setattr(supervisor, "_translator", dummy_translator)

    payload = {
        "id": "msg-1",
        "sender": "client",
        "locale": "lg",
        "messages": [
            {"format": "text", "content": "omuceere gwange gulabye"}
        ]
    }

    resp = client.post("/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == "msg-1"
    assert data["receiver"] == "client"
    assert data["messages"][0]["content"] == "ebirime birabika bulungi"
    assert data["messages"][0]["label"] == "analysis:lg"
    assert data["sender"] == "supervisor"
    assert dummy_translator.calls == [
        ("omuceere gwange gulabye", "en"),
        ("the crop looks healthy", "lg"),
    ]


def test_process_endpoint_no_text_messages():
    client = TestClient(app)

    payload = {
        "schema": "nlip/v1",
        "id": "msg-2",
        "sender": "client",
        "messages": [
            {"format": "image", "content": "mock-image-id"}
        ]
    }

    resp = client.post("/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == "msg-2"
    assert data["messages"][0]["label"] == "error"
    assert "No text messages" in data["messages"][0]["content"]

    """