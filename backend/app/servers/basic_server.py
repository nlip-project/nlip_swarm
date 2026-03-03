import os
import argparse

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from ..agents.nlip_agent import NlipAgent

from ..http_server.nlip_session_server import SessionManager, NlipSessionServer
import uvicorn
from app._logging import logger


class BasicManager(SessionManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.myAgent = NlipAgent(
            "BasicAgent"
        )
    
    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()

        try:
            results = await self.myAgent.process_query(text)
            logger.info(f"BasicServerResults: {results}")
            msg = NLIP_Factory.create_text(results[0])
            for res in results[1:]:
                msg.add_text(res)
            return msg
        except Exception as e:
            logger.error(f"Exception: {e}")
            error_msg = f"Exception: {e}"
            return NLIP_Factory.create_text(error_msg)

app = NlipSessionServer("basic", BasicManager)