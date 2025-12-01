import os
import argparse
import logging
import asyncio
import json
from typing import Any

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message, AllowedFormats

from ..agents.coordinator_nlip_agent import CoordinatorNlipAgent, connect_to_server
from ..http_server.nlip_session_server import NlipSessionServer, SessionManager
from ..agents.sound import transcribe_audio
from ..system.config import DEFAULT_AGENT_ENDPOINTS
from app._logging import logger

def _clean_outputs(outputs: list[str]) -> list[str]:
    cleaned = [entry for entry in outputs if entry and not entry.startswith("Calling tool:")]
    return cleaned or [""]


class NlipManager(SessionManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.agent = CoordinatorNlipAgent("Coordinator")
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
        # Fast-path: if the inbound payload is audio, bypass the LLM tool-calling
        # path to avoid stuffing large base64 into the coordinator context.
        fmt = getattr(msg, "format", None)
        fmt_text = str(fmt).lower() if fmt is not None else ""
        if "audio" in fmt_text:
            audio_payload = getattr(msg, "content", None)
            if not audio_payload:
                return NLIP_Factory.create_text("Audio payload missing for transcription.")

            mimetype = getattr(msg, "subformat", None) or "audio/wav"
            try:
                transcript = await transcribe_audio(audio_payload, mimetype=mimetype)
                return NLIP_Factory.create_text(transcript)
            except Exception as exc:
                logger.exception("Audio fast-path failed: %s", exc)
                return NLIP_Factory.create_text(f"Unable to transcribe audio: {exc}")

        text = msg.extract_text()

        try:
            results = await self.agent.process_query(text)
            logger.info(f"CoordinatorServerResults: {results}")
            msg = NLIP_Factory.create_text(results[0])
            for res in results[1:]:
                msg.add_text(res)
            return msg
        except Exception as e:
            logger.error(f"Exception: {e}")
            error = f"Exception: {e}"
            return NLIP_Factory.create_text(error)


app = NlipSessionServer("NlipCoordinatorCookie", NlipManager)