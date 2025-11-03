import base64
import binascii
import os
from collections.abc import Iterable as IterableABC
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx

from .translation import OllamaTranslationAgent, TranslationError

try:  # pragma: no cover - optional dependency for local dev
    from nlip_sdk import nlip  # type: ignore
except ImportError:  # pragma: no cover - allow unit tests to run without the SDK
    nlip = None  # type: ignore


class SoundAgentError(Exception):
    """Base exception raised when the sound agent cannot complete a request."""


class MissingAudioError(SoundAgentError):
    """Raised when no audio payloads are found inside the NLIP message."""


class AudioDecodingError(SoundAgentError):
    """Raised when audio content could not be decoded into raw bytes."""


class TranscriptionServiceError(SoundAgentError):
    """Raised when Whisper or downstream components fail."""


@dataclass
class AudioPayload:
    data: bytes
    mimetype: str
    label: str
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transcript:
    text: str
    language: Optional[str]
    sample: AudioPayload
    raw_response: Dict[str, Any]


class SoundAgent:
    """
    Convert NLIP audio payloads into localized text responses by chaining:

    audio -> Whisper transcription -> optional Ollama translation.
    """

    def __init__(
        self,
        *,
        whisper_url: Optional[str] = None,
        whisper_endpoint: str = "/v1/audio/transcriptions",
        whisper_model: str = "large-v3",
        timeout: float = 90.0,
        translator: Optional[OllamaTranslationAgent] = None,
    ) -> None:
        self.whisper_url = (whisper_url or os.getenv("WHISPER_URL", "http://localhost:9002")).rstrip("/")
        self.whisper_endpoint = whisper_endpoint
        self.whisper_model = whisper_model
        self.timeout = timeout
        self.translator = translator or OllamaTranslationAgent()

    def process(
        self,
        payload: Any,
        *,
        target_locale: Optional[str] = None,
    ) -> Any:
        """
        Transcribe every NLIP audio submessage and optionally translate the
        aggregated transcript into the requested locale.

        Returns either an NLIP message (if the SDK is available) or a fallback
        dictionary in the same shape for unit tests.
        """
        samples = self._extract_audio_payloads(payload)
        transcripts = [
            self._transcribe(sample, language_hint=sample.language)
            for sample in samples
        ]

        aggregated_text = " ".join(t.text for t in transcripts if t.text)
        if not aggregated_text.strip():
            raise SoundAgentError("Transcription returned no text.")

        final_language = transcripts[0].language or samples[0].language or "en"
        final_text = aggregated_text
        if target_locale and self.translator:
            try:
                final_text = self.translator.translate(aggregated_text, target_locale)
                final_language = target_locale
            except TranslationError as exc:
                raise SoundAgentError(f"Translation failed: {exc}") from exc

        return self._build_response(final_text, final_language, transcripts)

    def _extract_audio_payloads(self, payload: Any) -> List[AudioPayload]:
        candidates = list(self._iter_message_candidates(payload))
        samples: List[AudioPayload] = []
        for idx, candidate in enumerate(candidates):
            if not self._is_audio_candidate(candidate):
                continue
            label = self._resolve_attr(candidate, "label") or f"audio:{idx}"
            content = self._resolve_attr(candidate, "content")
            if content is None:
                continue
            samples.append(self._decode_audio_content(content, label))

        if not samples:
            raise MissingAudioError("No audio submessages were found inside the NLIP payload.")
        return samples

    def _iter_message_candidates(self, payload: Any) -> Iterable[Any]:
        if payload is None:
            return

        stack = [payload]
        while stack:
            candidate = stack.pop()
            yield candidate
            submessages = self._resolve_attr(candidate, "submessages") or []
            if isinstance(submessages, IterableABC) and not isinstance(submessages, (str, bytes)):
                stack.extend(reversed(list(submessages)))

    @staticmethod
    def _resolve_attr(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _is_audio_candidate(self, candidate: Any) -> bool:
        fmt = self._resolve_attr(candidate, "format")
        return self._format_is_audio(fmt)

    @staticmethod
    def _format_is_audio(fmt: Any) -> bool:
        if fmt is None:
            return False
        if isinstance(fmt, str):
            return fmt.lower() == "audio"
        name = getattr(fmt, "name", None)
        if isinstance(name, str) and name.lower() == "audio":
            return True
        value = getattr(fmt, "value", None)
        if isinstance(value, str) and value.lower() == "audio":
            return True
        return str(fmt).lower() == "audio"

    def _decode_audio_content(self, content: Any, label: str) -> AudioPayload:
        if isinstance(content, (bytes, bytearray)):
            data = bytes(content)
            mimetype = "application/octet-stream"
            metadata: Dict[str, Any] = {}
            language = None
        elif isinstance(content, str):
            data = self._decode_base64_blob(content)
            mimetype = "application/octet-stream"
            metadata = {}
            language = None
        elif isinstance(content, dict):
            encoding = (content.get("encoding") or "base64").lower()
            blob = content.get("data") or content.get("blob")
            if blob is None:
                raise AudioDecodingError("Audio content dictionary is missing 'data'.")
            if isinstance(blob, (bytes, bytearray)):
                data = bytes(blob)
            else:
                if encoding != "base64":
                    raise AudioDecodingError(f"Unsupported audio encoding '{encoding}'.")
                data = self._decode_base64_blob(blob)
            language = content.get("language")
            mimetype = content.get("mimetype") or content.get("media_type") or "application/octet-stream"
            metadata = {
                k: v
                for k, v in content.items()
                if k not in {"data", "blob", "encoding"}
            }
        else:
            raise AudioDecodingError(f"Unsupported audio content type: {type(content)!r}")

        if not data:
            raise AudioDecodingError("Audio payload is empty.")

        return AudioPayload(
            data=data,
            mimetype=mimetype,
            label=label,
            language=language,
            metadata=metadata,
        )

    @staticmethod
    def _decode_base64_blob(blob: Any) -> bytes:
        if not isinstance(blob, str):
            raise AudioDecodingError("Base64 blobs must be strings.")
        try:
            return base64.b64decode(blob, validate=True)
        except (binascii.Error, ValueError) as exc:  # pragma: no cover - base64 validation
            raise AudioDecodingError("Audio content is not valid base64.") from exc

    def _transcribe(self, sample: AudioPayload, *, language_hint: Optional[str]) -> Transcript:
        files = {
            "audio": (
                f"{sample.label}.wav",
                sample.data,
                sample.mimetype or "application/octet-stream",
            )
        }
        data = {"model": self.whisper_model}
        if language_hint:
            data["language"] = language_hint
        endpoint = f"{self.whisper_url}{self.whisper_endpoint}"

        try:
            response = httpx.post(endpoint, data=data, files=files, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TranscriptionServiceError(f"Whisper request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TranscriptionServiceError("Whisper returned a non-JSON response.") from exc

        text = (payload.get("text") or payload.get("transcription") or "").strip()
        if not text:
            raise TranscriptionServiceError("Whisper response did not include transcript text.")

        detected_language = payload.get("language") or payload.get("detected_language") or language_hint
        return Transcript(
            text=text,
            language=detected_language,
            sample=sample,
            raw_response=payload,
        )

    def _build_response(self, text: str, language: Optional[str], transcripts: Sequence[Transcript]) -> Any:
        language = language or transcripts[0].language or "en"
        metadata = {
            "segments": [
                {
                    "text": transcript.text,
                    "language": transcript.language,
                    "source_label": transcript.sample.label,
                    "sample_metadata": transcript.sample.metadata,
                }
                for transcript in transcripts
            ]
        }

        if nlip:
            message = nlip.NLIP_Factory.create_text(
                text,
                language=language,
                label=f"audio_transcript:{language}",
            )
            metadata_msg = nlip.NLIP_SubMessage(
                format=getattr(nlip.AllowedFormats, "generic", None),
                subformat="audio_metadata",
                content=metadata,
                label="audio_metadata",
            )
            message.add_submessage(metadata_msg)
            return message

        # Fallback for test environments without the NLIP SDK installed.
        return {
            "format": "text",
            "subformat": "text",
            "label": f"audio_transcript:{language}",
            "language": language,
            "content": text,
            "metadata": metadata,
        }
