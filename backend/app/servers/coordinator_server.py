import os
import argparse

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from ..agents.coordinator_nlip_agent import CoordinatorNlipAgent
from ..http_server.nlip_session_server import SessionManager, NlipSessionServer
import uvicorn

class NlipManager(SessionManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.myAgent = CoordinatorNlipAgent(
            "Steve"
        )

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
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