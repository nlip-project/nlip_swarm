import os
import asyncio
import logging
from typing import Optional, Any

from googletrans import Translator

from .nlip_agent import NlipAgent

logger = logging.getLogger("NLIP")

#MODEL="openai/o4-mini"
#MODEL="ollama_chat/llama3.2:3b"
MODEL = "cerebras/llama3.3-70b"

translator = Translator()


# TOOL DEFINITION
async def get_translation(text: str, target_locale: str) -> str | None:
    """
    Translate `text` into `target_locale` using googletrans.
    Runs the blocking googletrans call in a worker thread.
    """
    async with Translator() as translator:
        try:
            result = await translator.translate(text, dest=target_locale)
            return result.text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return None

class TranslationNlipAgent(NlipAgent):
    """NLIP Translation Agent exposing a single translation tool."""

    def __init__(
        self,
        name: str = "Translate",
        model: str = MODEL,
        instruction: Optional[str] = None,
        tools = [get_translation],
    ) -> None:
        super().__init__(name=name, model=model, instruction=instruction, tools=tools)

        self.add_instruction("You are an agent with tools for translating text between languages.")

        if instruction:
            self.add_instruction(instruction)
