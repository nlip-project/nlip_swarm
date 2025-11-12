import os
import asyncio
from typing import Optional, Any
import httpx

from .nlip_agent import NlipAgent

TRANSLATION_API="https://libretranslate.com/translate"
MODEL="ollama_chat/llama3.2:3b"

async def make_lt_request(text: str, target_lang: str, source_lang: str = "auto") -> str | None:
    url = TRANSLATION_API
    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": "text"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("translatedText", "")
        except Exception:
            return None

#TOOL DEFINITION
async def get_translation(text: str, target_locale: str) -> str | None:
    translation = await make_lt_request(text, target_locale)
    return translation

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
