import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
import pytest

from backend.app.agents.sound import (
    AudioDecodingError,
    MissingAudioError,
    SoundAgent,
    TranscriptionServiceError,
)


class DummyResponse:
    def __init__(self, json_data=None, status_ok=True):
        self._json_data = json_data or {}
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "http://test"),
                response=httpx.Response(500),
            )

    def json(self):
        return self._json_data


class StubTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, text, target_locale=None):
        self.calls.append((text, target_locale))
        return f"{text}::{target_locale}"


def test_sound_agent_process_transcribes_and_translates(monkeypatch):
    audio_bytes = b"fake-audio-bytes"
    message = {
        "submessages": [
            {
                "format": "audio",
                "label": "input-audio",
                "content": {
                    "encoding": "base64",
                    "mimetype": "audio/wav",
                    "language": "es",
                    "data": base64.b64encode(audio_bytes).decode("ascii"),
                },
            }
        ]
    }
    translator = StubTranslator()
    agent = SoundAgent(whisper_url="http://whisper.test", translator=translator, timeout=5)

    def fake_post(url, *, data=None, files=None, timeout=None):
        assert url == "http://whisper.test/v1/audio/transcriptions"
        assert data["model"] == agent.whisper_model
        assert data["language"] == "es"
        assert files["audio"][1] == audio_bytes
        assert timeout == 5
        return DummyResponse({"text": "hola mundo", "language": "es"})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = agent.process(message, target_locale="en")

    assert translator.calls == [("hola mundo", "en")]
    assert result["content"] == "hola mundo::en"
    assert result["language"] == "en"
    assert result["metadata"]["segments"][0]["text"] == "hola mundo"
    assert result["metadata"]["segments"][0]["source_label"] == "input-audio"


def test_sound_agent_raises_for_invalid_audio_blob():
    message = {
        "submessages": [
            {
                "format": "audio",
                "content": {
                    "encoding": "base64",
                    "data": "###not-base64###",
                },
            }
        ]
    }
    agent = SoundAgent(whisper_url="http://whisper.test")
    with pytest.raises(AudioDecodingError):
        agent.process(message)


def test_sound_agent_raises_on_missing_audio():
    agent = SoundAgent(whisper_url="http://whisper.test")
    message = {"submessages": []}
    with pytest.raises(MissingAudioError):
        agent.process(message)


def test_sound_agent_raises_on_whisper_http_failure(monkeypatch):
    audio_bytes = base64.b64encode(b"audio").decode("ascii")
    message = {
        "submessages": [
            {
                "format": "audio",
                "content": {"encoding": "base64", "data": audio_bytes},
            }
        ]
    }
    agent = SoundAgent(whisper_url="http://whisper.test")

    def fake_post(*args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(TranscriptionServiceError):
        agent.process(message)
