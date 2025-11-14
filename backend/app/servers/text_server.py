from __future__ import annotations

"""NLIP server wrapper for the TextNlipAgent."""

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from app.agents.textAgent import TextNlipAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager


class TextSessionManager(SessionManager):
    def __init__(self) -> None:
        self.agent = TextNlipAgent("text")

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()
        if not text:
            return NLIP_Factory.create_text("Text agent expects textual content.")

        try:
            results = await self.agent.process_query(text)
        except Exception as exc:  # pragma: no cover - defensive logging
            return NLIP_Factory.create_text(f"Error processing text request: {exc}")

        response = NLIP_Factory.create_text(results[0] if results else "")
        for extra in results[1:]:
            response.add_text(extra)
        return response


app = NlipSessionServer("TextAgentCookie", TextSessionManager)
