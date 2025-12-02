from __future__ import annotations

"""NLIP server wrapper for the SoundNlipAgent."""

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from app.agents.sound import SoundNlipAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager


CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}


def _capabilities_text(agent: SoundNlipAgent) -> str:
    capabilities = [
        "SPEECH_TO_TEXT:Transcribes base64-encoded audio via the transcribe_audio tool (Whisper-compatible endpoint).",
        "LANGUAGE_HINT:Accepts optional language hints to improve recognition accuracy.",
        "OPTIONAL_TRANSLATION:Can translate the transcript to a target locale when provided.",
    ]
    return f"AGENT:{agent.name}\n" + ", ".join(capabilities)


def _clean_outputs(outputs: list[str]) -> list[str]:
    cleaned = [entry for entry in outputs if entry and not entry.startswith("Calling tool:")]
    return cleaned or [""]


class SoundSessionManager(SessionManager):
    def __init__(self) -> None:
        self.agent = SoundNlipAgent("sound")

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()

        if text:
            normalized = text.strip().lower()
            if normalized in CAP_QUERY_PHRASES:
                return NLIP_Factory.create_text(_capabilities_text(self.agent))

        try:
            raw_results = await self.agent.process_nlip(msg)
        except Exception as exc:  # pragma: no cover - defensive logging
            return NLIP_Factory.create_text(f"Error processing sound request: {exc}")

        results = _clean_outputs(raw_results)
        response = NLIP_Factory.create_text(results[0])
        for extra in results[1:]:
            response.add_text(extra)
        return response


app = NlipSessionServer("SoundAgentCookie", SoundSessionManager)
