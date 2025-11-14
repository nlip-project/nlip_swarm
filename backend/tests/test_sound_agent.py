import base64
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.agents.sound import transcribe_audio


class DummyResponse:
    def __init__(self, data=None, status_ok=True):
        self.data = data or {}
        self.status_ok = status_ok

    def raise_for_status(self):
        if not self.status_ok:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("POST", "http://test"),
                response=httpx.Response(500),
            )

    def json(self):
        return self.data


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.captured = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, *, data=None, files=None):
        self.captured = {"url": url, "data": data, "files": files}
        return self.response


@pytest.mark.asyncio
async def test_transcribe_audio_calls_whisper(monkeypatch):
    audio = base64.b64encode(b"audio-bytes").decode()

    dummy_client = DummyClient(
        DummyResponse({"text": "hola mundo", "language": "es"})
    )

    monkeypatch.setattr(
        "backend.app.agents.sound.httpx.AsyncClient", lambda timeout: dummy_client
    )

    result = await transcribe_audio(audio, language_hint="es")

    assert "Transcript (es): hola mundo" in result
    assert dummy_client.captured["data"]["language"] == "es"
    assert dummy_client.captured["files"]["audio"][1] == base64.b64decode(audio)


@pytest.mark.asyncio
async def test_transcribe_audio_handles_translation(monkeypatch):
    audio = base64.b64encode(b"audio").decode()
    dummy_client = DummyClient(DummyResponse({"text": "bonjour", "language": "fr"}))

    monkeypatch.setattr(
        "backend.app.agents.sound.httpx.AsyncClient", lambda timeout: dummy_client
    )

    async def fake_translation(text, target_locale):
        return f"{text}::{target_locale}"

    monkeypatch.setattr(
        "backend.app.agents.sound.get_translation", fake_translation
    )

    result = await transcribe_audio(audio, target_locale="en")

    assert "Translated (en): bonjour::en" in result


@pytest.mark.asyncio
async def test_transcribe_audio_invalid_base64():
    result = await transcribe_audio("not-base64:::")
    assert "could not be decoded" in result.lower()


@pytest.mark.asyncio
async def test_transcribe_audio_handles_http_error(monkeypatch):
    audio = base64.b64encode(b"audio").decode()
    response = DummyResponse(status_ok=False)
    dummy_client = DummyClient(response)

    monkeypatch.setattr(
        "backend.app.agents.sound.httpx.AsyncClient", lambda timeout: dummy_client
    )

    result = await transcribe_audio(audio)
    assert "unable to transcribe" in result.lower()
