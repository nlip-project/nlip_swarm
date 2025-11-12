from __future__ import annotations

"""
NLIP server wrapper for the OllamaTranslationAgent, mounted as a FastAPI app.

This exposes a sessioned /nlip endpoint for the translation agent so it can be
addressed via mem://translate by the Coordinator.
"""

from nlip_sdk.nlip import NLIP_Message, NLIP_Factory

from app.agents.translation import OllamaTranslationAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager


CAP_QUERY_PHRASES = {
    "what are your nlip capabilities?",
    "describe your nlip capabilities.",
}


def _capabilities_text(agent: OllamaTranslationAgent) -> str:
    caps = agent.capabilities if hasattr(agent, "capabilities") else []
    pairs = ", ".join(f"{c}:handles {c}" for c in caps)
    return f"AGENT:{agent.name}\n{pairs}"


class TranslateSessionManager(SessionManager):
    def __init__(self) -> None:
        self.agent = OllamaTranslationAgent()

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()
        if text and text.strip().lower() in CAP_QUERY_PHRASES:
            return NLIP_Factory.create_text(_capabilities_text(self.agent))
        return await self.agent.handle(msg)


# The ASGI app registered for mem://translate
app = NlipSessionServer("TranslateAgentCookie", TranslateSessionManager)

