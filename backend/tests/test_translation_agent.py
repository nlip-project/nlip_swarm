import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
import pytest
import os

from backend.app.agents.translation import OllamaTranslationAgent, TranslationError


class DummyResponse:
    def __init__(self, *, json_data=None, status_ok=True, status_code=None, text=None):
        self._json_data = json_data or {}
        self._status_ok = status_ok
        self.status_code = 200 if status_code is None else status_code
        if text is not None:
            self.text = text
        else:
            try:
                import json as _json
                self.text = _json.dumps(self._json_data)
            except Exception:
                self.text = str(self._json_data)

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "http://test"),
                response=httpx.Response(500),
            )

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


def test_translate_success(monkeypatch):
    agent = OllamaTranslationAgent(base_url="http://ollama.test", model="mock-model")

    def fake_post(url, *, json, timeout):
        assert url == "http://ollama.test/api/generate"
        assert json["model"] == "mock-model"
        assert "hola" not in json["prompt"]
        assert timeout == agent.timeout
        return DummyResponse(json_data={"response": "hola"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert agent.translate("hello", "es") == "hola"


def test_translate_defaults_to_en(monkeypatch):
    agent = OllamaTranslationAgent(base_url="http://ollama.test")

    def fake_post(url, *, json, timeout):
        assert "locale 'en'" in json["prompt"]
        assert json["model"] == "llama3.1"
        return DummyResponse(json_data={"response": "hello"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert agent.translate("hola") == "hello"


def test_translate_empty_text_raises():
    agent = OllamaTranslationAgent()
    with pytest.raises(TranslationError):
        agent.translate("", "es")


def test_translate_http_error(monkeypatch):
    agent = OllamaTranslationAgent()

    def fake_post(*args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(TranslationError) as excinfo:
        agent.translate("hola", "en")
    assert "Ollama request failed" in str(excinfo.value)


def test_translate_non_json_response(monkeypatch):
    agent = OllamaTranslationAgent()

    def fake_post(*args, **kwargs):
        return DummyResponse(json_data=ValueError("bad json"))

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(TranslationError) as excinfo:
        agent.translate("hola", "en")
    assert "non-JSON" in str(excinfo.value)


def test_translate_missing_response_key(monkeypatch):
    agent = OllamaTranslationAgent()

    def fake_post(*args, **kwargs):
        return DummyResponse(json_data={"foo": "bar"})

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(TranslationError) as excinfo:
        agent.translate("hola", "en")
    assert "did not include translated text" in str(excinfo.value)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("RUN_OLLAMA_TESTS"),
    reason="Set RUN_OLLAMA_TESTS=1 to exercise the live Ollama endpoint."
)
def test_translate_with_live_ollama():
    agent = OllamaTranslationAgent()
    source_text = "Je, mmea huu unaonekana kuwa na afya?"  # Swahili for "Does this plant look healthy?"
    try:
        result = agent.translate(source_text, "en")
    except TranslationError as exc:
        pytest.skip(f"Ollama translation failed ({exc}); ensure the local server is running.")
    translated = result.strip()
    print(f"Ollama returned: {translated}")
    assert translated
    assert translated.lower() != source_text.lower()
