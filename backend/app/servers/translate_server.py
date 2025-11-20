import os
import argparse

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from ..agents.translation import TranslationNlipAgent
from ..http_server.nlip_session_server import SessionManager, NlipSessionServer
import uvicorn
from app._logging import logger

CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}


def _capabilities_text(agent: TranslationNlipAgent) -> str:
    capabilities = [
        "TRANSLATE_TEXT:Translates text to a specified target locale using the get_translation tool.",
        "DETECT_LANGUAGE:Auto-detects source language when not provided.",
        "PRESERVE_STRUCTURE:Keeps punctuation and formatting intact where possible.",
    ]
    return f"AGENT:{agent.name}\n" + ", ".join(capabilities)


def _clean_outputs(outputs: list[str]) -> list[str]:
    cleaned = [entry for entry in outputs if entry and not entry.startswith("Calling tool:")]
    return cleaned or [""]

CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}


def _capabilities_text(agent: TranslationNlipAgent) -> str:
    capabilities = [
        "TRANSLATE_TEXT:Translates text to a specified target locale using the get_translation tool.",
        "DETECT_LANGUAGE:Auto-detects source language when not provided.",
        "PRESERVE_STRUCTURE:Keeps punctuation and formatting intact where possible.",
    ]
    return f"AGENT:{agent.name}\n" + ", ".join(capabilities)


def _clean_outputs(outputs: list[str]) -> list[str]:
    cleaned = [entry for entry in outputs if entry and not entry.startswith("Calling tool:")]
    return cleaned or [""]

class TranslationManager(SessionManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.myAgent = TranslationNlipAgent(
            "translate"
        )
    
    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()

        if not text:
            return NLIP_Factory.create_text("Translation agent expects textual content.")

        normalized = text.strip().lower()
        if normalized in CAP_QUERY_PHRASES:
            return NLIP_Factory.create_text(_capabilities_text(self.myAgent))

        try:
            results = await self.myAgent.process_query(text)
            logger.info(f"TranslationServerResults: {results}")
            clean = _clean_outputs(results)
            resp = NLIP_Factory.create_text(clean[0])
            for res in clean[1:]:
                resp.add_text(res)
            return resp
        except Exception as e:
            logger.error(f"Exception: {e}")
            error_msg = f"Exception: {e}"
            return NLIP_Factory.create_text(error_msg)
        
app = NlipSessionServer("TranslationCookie", TranslationManager)
