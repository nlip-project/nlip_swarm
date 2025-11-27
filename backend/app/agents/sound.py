"""Sound agent exposing NLIP-friendly transcription tools."""

from __future__ import annotations

import base64
import binascii
import logging
import os
from typing import Optional

import httpx

from .nlip_agent import NlipAgent
from .base import MODEL
from .translation import get_translation


logger = logging.getLogger("NLIP")


WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:9002").rstrip("/")
WHISPER_ENDPOINT = os.getenv("WHISPER_ENDPOINT", "/v1/audio/transcriptions")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
WHISPER_TIMEOUT = float(os.getenv("WHISPER_TIMEOUT", "90.0"))


def _strip_data_url(audio_base64: str) -> str:
    if "," in audio_base64 and audio_base64.strip().startswith("data:"):
        return audio_base64.split(",", 1)[1]
    return audio_base64


def _decode_audio(audio_base64: str) -> bytes | None:
    clean_b64 = _strip_data_url(audio_base64)
    try:
        return base64.b64decode(clean_b64, validate=True)
    except (binascii.Error, ValueError):  # pragma: no cover - invalid user input
        return None


async def transcribe_audio(
    audio_base64: str,
    mimetype: str = "audio/wav",
    language_hint: Optional[str] = None,
    target_locale: Optional[str] = None,
) -> str:
    """Transcribe audio using a Whisper-compatible server.

    Args:
        audio_base64: Base64 encoded audio (optionally as a data URL).
        mimetype: MIME type passed to Whisper for better decoding.
        language_hint: Optional ISO language code to help Whisper.
        target_locale: Optional locale for automatic translation of the transcript.
    """

    audio_bytes = _decode_audio(audio_base64)
    if not audio_bytes:
        return "Audio payload could not be decoded. Provide base64 encoded audio."

    files = {"audio": ("audio.wav", audio_bytes, mimetype or "application/octet-stream")}
    data = {"model": WHISPER_MODEL}
    if language_hint:
        data["language"] = language_hint

    url = f"{WHISPER_URL}{WHISPER_ENDPOINT}"
    logger.debug("Sound agent calling Whisper", extra={"url": url, "model": WHISPER_MODEL})

    async with httpx.AsyncClient(timeout=WHISPER_TIMEOUT) as client:
        try:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
        except httpx.HTTPError as exc:  
            logger.exception("Whisper request failed: %s", exc)
            return "Unable to transcribe the audio because the Whisper request failed."

    try:
        payload = response.json()
    except ValueError:
        logger.exception("Whisper response was not valid JSON")
        return "Unable to transcribe the audio because the Whisper response was invalid."

    transcript = (payload.get("text") or payload.get("transcription") or "").strip()
    if not transcript:
        return "Transcription service returned no text."

    detected_language = payload.get("language") or payload.get("detected_language") or language_hint or "unknown"
    lines = [f"Transcript ({detected_language}): {transcript}"]

    if target_locale and target_locale != detected_language:
        translation = await get_translation(transcript, target_locale)
        if translation:
            lines.append(f"Translated ({target_locale}): {translation}")
        else:  # pragma: no cover - depends on remote API
            lines.append(f"Translation to {target_locale} was requested but failed.")

    return "\n".join(lines)


class SoundNlipAgent(NlipAgent):
    """NLIP agent exposing the `transcribe_audio` tool."""

    def __init__(
        self,
        name: str = "Sound",
        model: str = MODEL,
        instruction: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, model=model, instruction=instruction, tools=[transcribe_audio])

        self.add_instruction(
            "You understand how to invoke the `transcribe_audio` tool for speech-to-text tasks."
        )
