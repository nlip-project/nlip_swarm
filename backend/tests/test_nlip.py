import app.routes.health as health
import app.routes.nlip as nlip
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from typing import Any, Dict, Optional

from backend import app

class DummySession:
    def __init__(self, response: Optional[Dict[str, Any]] = None, raise_exc: Optional[Exception] = None):
        self.raise_exc = raise_exc
        self.started = False
        self.stopped = False
        self.response = response or {"status": "ok"}
        self.correlated_calls = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    async def correlated_execute(self, message):
        self.correlated_calls.append(message)
        if self.raise_exc:
            raise self.raise_exc
        return self.response
    
class DummyClientApp:
    def __init__(self, session: DummySession):
        self._session = session
        self.added = []
        self.removed = []

    def create_session(self):
        return self._session
    
    def add_session(self, session):
        self.added.append(session)

    def remove_session(self, session):
        self.removed.append(session)


    def build_with_dummy(self, session: DummySession) -> FastAPI:
        app = FastAPI()
        app.include_router(health.router, prefix="/health")
        app.include_router(nlip.router, prefix="/nlip")
        app.state.client_app = DummyClientApp(session)
        return app

def test_health_check():
    client = TestClient(app)
    resp = client.get("/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

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