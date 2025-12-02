from __future__ import annotations

"""NLIP server wrapper for the ImageNlipAgent."""

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from app.agents.imageRecognition import ImageNlipAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager


CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}


def _capabilities_text(agent: ImageNlipAgent) -> str:
    capabilities = [
        "IMAGE_DESCRIPTION:Describes images using Llava model|FORMATS:[binary]|SUBFORMATS:[image]",
        "PROMPT_GUIDANCE:Accepts optional prompts|FORMATS:[text]",
        "DATA_URL_STRIPPING:Handles base64 or data URLs",
    ]
    return f"AGENT:{agent.name}\n" + ", ".join(capabilities)


def _clean_outputs(outputs: list[str]) -> list[str]:
    cleaned = [entry for entry in outputs if entry and not entry.startswith("Calling tool:")]
    return cleaned or [""]


class ImageSessionManager(SessionManager):
    def __init__(self) -> None:
        self.agent = ImageNlipAgent("image")

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()

        if text:
            normalized = text.strip().lower()
            if normalized in CAP_QUERY_PHRASES:
                return NLIP_Factory.create_text(_capabilities_text(self.agent))

        try:
            raw_results = await self.agent.process_nlip(msg)
        except Exception as exc:  # pragma: no cover
            return NLIP_Factory.create_text(f"Error processing image request: {exc}")

        results = _clean_outputs(raw_results)
        response = NLIP_Factory.create_text(results[0])
        for extra in results[1:]:
            response.add_text(extra)
        return response


app = NlipSessionServer("ImageAgentCookie", ImageSessionManager)
