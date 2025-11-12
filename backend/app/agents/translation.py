import os
import asyncio
from typing import Optional

from litellm import completion

from .nlip_agent import NlipAgent
from .base import MODEL


class TranslationError(Exception):
    """Raised when the translation tool cannot complete a request."""


async def _llm_translate_request(model: str, text: str, target_lang: str) -> str:
    """Helper: perform a litellm completion to translate text to target_locale.

    Uses a strict system instruction so the result is just the translated text.
    """
    if not text:
        raise TranslationError("Cannot translate empty text input.")

    system = (
        "You are a translation engine. Translate the user text into the "
        f"locale '{target_lang}'. Output only the translation, no extras."
    )
    user = f"Text to translate:\n{text}"

    def _call():
        resp = completion(model=model, messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=False)
        msg = getattr(resp.choices[0], "message", None)
        content = getattr(msg, "content", None) if msg is not None else None
        if not content:
            raise TranslationError("Empty response from model")
        return str(content).strip()

    return await asyncio.to_thread(_call)


# TOOL Definition
async def get_translation(text: str, target_lang: str) -> str:
    """Translate the provided text into the target language using the configured LLM model.

    Args:
        text: Source text to translate
        target_lang: Language to translate to (e.g., 'en', 'es-ES')
    """
    model = os.getenv("AGENT_MODEL", MODEL)
    return await _llm_translate_request(model, text, target_lang or "en")


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

        self.add_instruction(
            "You have one tool: get_translation(text, target_locale). "
            "Use it to translate user text into the specified target locale and return only the translation."
        )
