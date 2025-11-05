import sys
from pathlib import Path
import types
import pytest
from typing import Any, cast
from fastapi.testclient import TestClient
import importlib


def _install_stubs_before_import():
    # Stub langdetect
    ld_mod = types.ModuleType("langdetect")
    setattr(ld_mod, "LangDetectException", Exception)
    setattr(ld_mod, "detect", lambda text: "en")
    sys.modules.setdefault("langdetect", ld_mod)

    # Stub nlip_sdk.nlip
    nlip_pkg = types.ModuleType("nlip_sdk")
    nlip_sub = types.ModuleType("nlip_sdk.nlip")

    class _DummyMsg:
        def __init__(self, content=None, label=None, messagetype=None, format=None, subformat=None, submessages=None):
            self.content = content
            self.label = label
            self.messagetype = messagetype
            self.format = format
            self.subformat = subformat
            self.submessages = submessages or []

        @classmethod
        def model_validate(cls, payload):
            return cls(**payload)

        def to_dict(self):
            return {
                "content": self.content,
                "label": self.label,
                "messagetype": self.messagetype,
                "format": self.format,
                "subformat": self.subformat,
                "submessages": self.submessages,
            }

    class _DummyFactory:
        @staticmethod
        def create_json(content, messagetype="response"):
            return _DummyMsg(content=content, messagetype=messagetype)

        @staticmethod
        def create_text(text, label=""):
            return _DummyMsg(content=text, label=label, format="text")

    class _Allowed:
        generic = "generic"
        text = "text"

    class _SubMsg(_DummyMsg):
        pass

    nlip_sub_any = cast(Any, nlip_sub)
    nlip_sub_any.NLIP_Message = _DummyMsg
    nlip_sub_any.NLIP_Factory = _DummyFactory
    nlip_sub_any.AllowedFormats = _Allowed
    nlip_sub_any.NLIP_SubMessage = _SubMsg
    sys.modules.setdefault("nlip_sdk", nlip_pkg)
    sys.modules.setdefault("nlip_sdk.nlip", nlip_sub)

    lc_mod = types.ModuleType("langchain_ollama")

    class _ChatOllama:
        def __init__(self, *args, **kwargs):
            pass

        async def ainvoke(self, prompt):
            return types.SimpleNamespace(content='{"agent_name":"ollama_translation","reasoning":"stub"}')

    lc_any = cast(Any, lc_mod)
    lc_any.ChatOllama = _ChatOllama
    sys.modules.setdefault("langchain_ollama", lc_mod)

    try:
        backend_app = importlib.import_module("backend.app")
        sys.modules.setdefault("app", backend_app)
    except Exception:
        pass


def test_capabilities_returns_registered_agents(monkeypatch):
    _install_stubs_before_import()
    import backend.app.main as main

    class DummyMsg:
        def __init__(self, content, messagetype):
            self._content = content
            self._messagetype = messagetype

        def to_dict(self):
            return {"content": self._content, "messagetype": self._messagetype}

    class DummyFactory:
        @staticmethod
        def create_json(content, messagetype="response"):
            return DummyMsg(content, messagetype)

    monkeypatch.setattr(main, "NLIP_Factory", DummyFactory)

    client = TestClient(main.app)
    resp = client.get("/capabilities")
    assert resp.status_code == 200

    data = resp.json()
    assert data.get("messagetype") == "response"
    assert isinstance(data.get("content"), dict)
    assert "ollama_translation" in data["content"]
    assert set(data["content"]["ollama_translation"]) == {"task.translate.*", "task.translate"}


def test_nlip_delegates_to_swarm_manager(monkeypatch):
    _install_stubs_before_import()
    import backend.app.main as main

    def fake_from_dict(payload):
        return types.SimpleNamespace(kind="parsed", payload=payload)

    def fake_to_dict(obj):
        return {"echo": getattr(obj, "result", None)}

    result_obj = types.SimpleNamespace(result="ok")

    async def fake_handle(message):
        assert getattr(message, "kind", None) == "parsed"
        return result_obj

    monkeypatch.setattr(main, "from_dict", fake_from_dict)
    monkeypatch.setattr(main, "to_dict", fake_to_dict)
    monkeypatch.setattr(main, "swarm_manager", types.SimpleNamespace(handle=fake_handle))

    client = TestClient(main.app)
    payload = {"format": "text", "content": "hello"}
    resp = client.post("/nlip", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"echo": "ok"}
