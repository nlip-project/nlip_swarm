import os
import argparse
import logging
import asyncio
import json
from typing import Any

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message, AllowedFormats
from ..agents.coordinator_nlip_agent import CoordinatorNlipAgent
from ..agents.sound import transcribe_audio
from ..http_server.nlip_session_server import SessionManager, NlipSessionServer
from ..system.config import DEFAULT_AGENT_ENDPOINTS
import uvicorn
from app._logging import logger


class NlipManager(SessionManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.myAgent = CoordinatorNlipAgent("Coordinator")
        self._initialized = False

    async def _ensure_connected(self) -> None:
        if self._initialized:
            return

        for url in DEFAULT_AGENT_ENDPOINTS:
            try:
                await connect_to_server(url)  # type: ignore[arg-type]
            except Exception as exc:
                logger.error(f"Failed to connect coordinator to {url!r}: {exc}")

        self._initialized = True

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        logger.debug(msg)
        media_audio = _collect_media(msg, kind_match="audio")
        if media_audio:
            audio_payload, mimetype = media_audio[0]
            try:
                transcript = await transcribe_audio(audio_payload, mimetype=mimetype)
                return NLIP_Factory.create_text(transcript)
            except Exception as exc:
                logger.exception("Audio fast-path failed: %s", exc)
                return NLIP_Factory.create_text(f"Unable to transcribe audio: {exc}")

        coordinator_query = build_coordinator_prompt_view(msg)

        try:
            results = await self.myAgent.process_query(coordinator_query)
            logger.info(f"CoordinatorServerResults: {results}")
            msg_out = NLIP_Factory.create_text(results[0])
            for res in results[1:]:
                msg_out.add_text(res)
            return msg_out
        except Exception as e:
            logger.error(f"Exception: {e}")
            error = f"Exception: {e}"
            return NLIP_Factory.create_text(error)


app = NlipSessionServer("NlipCoordinatorCookie", NlipManager)


def _iter_parts(msg: NLIP_Message):
    """Yield (format, subformat, label, content) for top-level and submessages."""
    yield msg.format, msg.subformat, msg.label, msg.content
    for sub in getattr(msg, "submessages", []) or []:
        yield sub.format, getattr(sub, "subformat", None), getattr(sub, "label", None), getattr(sub, "content", None)


def _classify(format_val: Any, subformat_val: Any) -> str:
    fmt = str(format_val or "").lower()
    sub = str(subformat_val or "").lower()
    if fmt == AllowedFormats.text:
        return "text"
    if fmt == AllowedFormats.token:
        return "token"
    if fmt == AllowedFormats.structured:
        return "structured"
    if fmt == AllowedFormats.location:
        return "location"
    if fmt == AllowedFormats.error:
        return "error"
    if fmt == AllowedFormats.generic:
        return "generic"
    if fmt == AllowedFormats.binary or fmt == "binary":
        if sub.startswith("audio/"):
            return "audio"
        if sub.startswith("image/"):
            return "image"
        if sub.startswith("video/"):
            return "video"
        return "binary"
    return "unknown"


def _collect_media(msg: NLIP_Message, kind_match: str) -> list[tuple[Any, str]]:
    """
    Collect all media payloads (audio/image/video) of the requested kind.
    Returns a list of (content, mimetype).
    """
    found: list[tuple[Any, str]] = []
    for fmt, subfmt, label, content in _iter_parts(msg):
        kind = _classify(fmt, subfmt)
        if kind == kind_match and content:
            mimetype = subfmt or f"{kind}/octet-stream"
            found.append((content, mimetype))
    return found


def _scrub_payload(payload: Any) -> None:
    """
    Scrub binary/media contents in-place on a dict/list copy to avoid
    stuffing large base64 into the coordinator LLM prompt.
    """
    if isinstance(payload, dict):
        fmt = str(payload.get("format", "")).lower()
        subfmt = str(payload.get("subformat", "")).lower()
        if fmt == "binary" or any(tok in subfmt for tok in ("audio", "image", "video")):
            content = payload.get("content")
            if isinstance(content, str) and len(content) > 64:
                payload["content"] = f"<omitted binary content (len={len(content)})>"
        for sub in payload.get("submessages") or []:
            _scrub_payload(sub)
    elif isinstance(payload, list):
        for item in payload:
            _scrub_payload(item)


def build_coordinator_prompt_view(msg: NLIP_Message) -> str:
    """
    Build a text prompt for the coordinator LLM that includes:
    - Aggregated text from the NLIP message.
    - A scrubbed JSON view of the full message (binary/media payloads replaced).
    - A raw JSON view of the full message (unscrubbed) for relay_nlip_to_server.
    """
    user_text = msg.extract_text() or ""
    payload_scrubbed = msg.to_dict()
    _scrub_payload(payload_scrubbed)
    payload_raw = msg.to_dict()

    parts = []
    if user_text:
        parts.append(f"User text (aggregated from NLIP message):\n{user_text}")
    parts.append(
        "Full NLIP_Message (scrubbed JSON; binary/media payloads replaced with placeholders – "
        "use only for reasoning, not for relay):"
    )
    parts.append(json.dumps(payload_scrubbed, indent=2, ensure_ascii=False))
    parts.append(
        "Full NLIP_Message (raw/unscrubbed JSON; use this when calling relay_nlip_to_server so media/base64 is preserved):"
    )
    parts.append(json.dumps(payload_raw, indent=2, ensure_ascii=False))
    return "\n\n".join(parts)
