import os
import argparse
import logging

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from ..agents.coordinator_nlip_agent import CoordinatorNlipAgent
from ..agents.sound import transcribe_audio
from ..http_server.nlip_session_server import SessionManager, NlipSessionServer
import uvicorn

logger = logging.getLogger("NLIP")

class NlipManager(SessionManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.myAgent = CoordinatorNlipAgent(
            "Coordinator"
        )

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
            results = await self.myAgent.process_query(text)
            msg = NLIP_Factory.create_text(results[0])
            for res in results[1:]:
                msg.add_text(res)
            return msg
        except Exception as e:
            error = f"Exception: {e}"
            return NLIP_Factory.create_text(error)
        
app = NlipSessionServer("NlipCoordinatorCookie", NlipManager)
