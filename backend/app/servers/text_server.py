from __future__ import annotations

"""
NLIP server wrapper for the LLamaTextAgent, mounted as a FastAPI app.

This exposes a sessioned /nlip endpoint for the text agent so it can be
addressed via mem://text by the Coordinator.
"""

from nlip_sdk.nlip import NLIP_Message, NLIP_Factory

from app.agents.textAgent import LLamaTextAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager


CAP_QUERY_PHRASES = {
    "what are your nlip capabilities?",
    "describe your nlip capabilities.",
}


def _capabilities_text(agent: LLamaTextAgent) -> str:
    caps = agent.capabilities if hasattr(agent, "capabilities") else []
    # Deterministic capability response expected by the Coordinator
    pairs = ", ".join(f"{c}:handles {c}" for c in caps)
    return f"AGENT:{agent.name}\n{pairs}"


class TextSessionManager(SessionManager):
    def __init__(self) -> None:
        self.agent = LLamaTextAgent()

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()
        if text and text.strip().lower() in CAP_QUERY_PHRASES:
            return NLIP_Factory.create_text(_capabilities_text(self.agent))
        return await self.agent.handle(msg)


# The ASGI app registered for mem://text
app = NlipSessionServer("TextAgentCookie", TextSessionManager)

