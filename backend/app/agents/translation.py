import os
import logging
from typing import Optional, Any, cast

from litellm import acompletion

from .nlip_agent import NlipAgent
from .base import MODEL as DEFAULT_MODEL, LOCAL_API_KEY

logger = logging.getLogger("NLIP")

_TRANSLATION_URL   = os.getenv("TRANSLATION_URL")
_TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL")
_OLLAMA_URL        = os.getenv("OLLAMA_URL")
_OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL")

if _TRANSLATION_URL and _TRANSLATION_MODEL:
    TRANSLATION_LLM_MODEL    = f"openai/{_TRANSLATION_MODEL}"
    TRANSLATION_LLM_API_BASE = _TRANSLATION_URL.rstrip("/")
elif _OLLAMA_URL and _OLLAMA_MODEL:
    TRANSLATION_LLM_MODEL    = f"openai/{_OLLAMA_MODEL}"
    TRANSLATION_LLM_API_BASE = _OLLAMA_URL.rstrip("/")
else:
    TRANSLATION_LLM_MODEL    = None
    TRANSLATION_LLM_API_BASE = None

MODEL    = TRANSLATION_LLM_MODEL or DEFAULT_MODEL
API_BASE = TRANSLATION_LLM_API_BASE


# TOOL DEFINITION
async def get_translation(text: str, target_locale: str) -> str | None:
    """Translate `text` into `target_locale`."""
    if not text or not text.strip():
        logger.warning("Translation requested with empty text", extra={"target_locale": target_locale})
        return None

    logger.info(
        "Translation request received",
        extra={
            "target_locale": target_locale,
            "input_len": len(text),
            "backend": "local-llm" if (TRANSLATION_LLM_MODEL and TRANSLATION_LLM_API_BASE) else "googletrans-fallback",
        },
    )

    if TRANSLATION_LLM_MODEL and TRANSLATION_LLM_API_BASE:
        messages = [
            {"role": "system", "content": "You are a professional translator. Output only the translated text."},
            {"role": "user", "content": f"Translate into '{target_locale}':\n\n{text}"},
        ]
        try:
            response = cast(Any, await acompletion(
                model=TRANSLATION_LLM_MODEL,
                messages=messages,
                api_base=TRANSLATION_LLM_API_BASE,
                api_key=LOCAL_API_KEY,
            ))
            content = response.choices[0].message.content
            logger.info(
                "Translation completed via local-llm",
                extra={"target_locale": target_locale, "output_len": len(content) if isinstance(content, str) else 0},
            )
            return content.strip() if isinstance(content, str) else None
        except Exception as e:
            logger.error(f"Local LLM translation error: {e}")
            return None
    else:
        # Fallback for local dev without Docker Model Runner
        from googletrans import Translator
        async with Translator() as translator:
            try:
                result = await translator.translate(text, dest=target_locale)
                logger.info(
                    "Translation completed via googletrans fallback",
                    extra={"target_locale": target_locale, "output_len": len(result.text) if isinstance(result.text, str) else 0},
                )
                return result.text
            except Exception as e:
                logger.error(f"Translation error: {e}")
                return None


class TranslationNlipAgent(NlipAgent):
    """NLIP Translation Agent exposing a single translation tool."""

    def __init__(
        self,
        name: str = "Translate",
        model: Optional[str] = MODEL,
        instruction: Optional[str] = None,
        tools: Optional[list] = None,
        api_base: Optional[str] = API_BASE,
    ) -> None:
        if tools is None:
            tools = [get_translation]
        super().__init__(name=name, model=model, instruction=instruction, tools=tools, api_base=api_base)

        self.add_instruction("You are an agent with tools for translating text between languages.")

        if instruction:
            self.add_instruction(instruction)
