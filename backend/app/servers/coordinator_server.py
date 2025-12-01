from __future__ import annotations

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from ..agents.coordinator_nlip_agent import CoordinatorNlipAgent, connect_to_server
from ..http_server.nlip_session_server import NlipSessionServer, SessionManager
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
        text = msg.extract_text()
        if not text:
            return NLIP_Factory.create_text("Coordinator agent expects textual content.")

        await self._ensure_connected()
        try:
            raw_results = await self.agent.process_nlip(msg)
            logger.info(f"CoordinatorServerResults: {raw_results}")
        except Exception as exc:
            logger.error(f"Exception: {exc}")
            return NLIP_Factory.create_text(f"Exception: {exc}")

        results = _clean_outputs(raw_results)
        response = NLIP_Factory.create_text(results[0])
        for res in results[1:]:
            response.add_text(res)
        return response


app = NlipSessionServer("NlipCoordinatorCookie", NlipManager)
