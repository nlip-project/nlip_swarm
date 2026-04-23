import os
import argparse
import re

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from ..agents.translation import TranslationNlipAgent, get_translation
from ..http_server.nlip_session_server import SessionManager, NlipSessionServer
import uvicorn
from app._logging import logger

CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}

LANGUAGE_TO_CODE = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "chinese": "zh-cn",
    "japanese": "ja",
    "korean": "ko",
}


def _parse_explicit_translation_request(text: str) -> tuple[str, str] | None:
    """
    Parse prompts like:
    - Translate this to Spanish: Hello
    - Translate to en: Hello
    Returns (source_text, target_locale).
    """
    if not text:
        return None

    match = re.match(r"^\s*translate(?:\s+this)?\s+to\s+([^:]+?)\s*:\s*(.+)\s*$", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    target_raw = match.group(1).strip().lower()
    source_text = match.group(2).strip()
    if not source_text:
        return None

    target_locale = LANGUAGE_TO_CODE.get(target_raw, target_raw)
    return (source_text, target_locale)


def _normalize_translated_text(text: str) -> str:
    """Remove common wrapper prefixes from LLM translation outputs."""
    if not text:
        return text

    cleaned = text.strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return cleaned

    first = lines[0].lower().rstrip(":")
    if (
        len(lines) > 1
        and (
            first in {
                "here is the translation",
                "translation",
                "translated text",
                "here's the translation",
            }
            or ("translation" in first and (first.startswith("here is") or first.startswith("here's") or first.startswith("heres")))
        )
    ):
        return "\n".join(lines[1:]).strip()

    return cleaned

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

        logger.info(
            "Translation server received request",
            extra={
                "has_text": bool(text and text.strip()),
                "text_len": len(text) if isinstance(text, str) else 0,
            },
        )

        if not text:
            return NLIP_Factory.create_text("Translation agent expects textual content.")

        normalized = text.strip().lower()
        if normalized in CAP_QUERY_PHRASES:
            return NLIP_Factory.create_text(_capabilities_text(self.myAgent))

        explicit_translation = _parse_explicit_translation_request(text)
        if explicit_translation:
            source_text, target_locale = explicit_translation
            logger.info(
                "Explicit translation intent matched",
                extra={
                    "target_locale": target_locale,
                    "source_len": len(source_text),
                },
            )
            translated = await get_translation(source_text, target_locale)
            if translated and translated.strip():
                normalized_text = _normalize_translated_text(translated)
                logger.info(
                    "Explicit translation completed",
                    extra={"target_locale": target_locale, "output_len": len(normalized_text)},
                )
                return NLIP_Factory.create_text(normalized_text)
            logger.warning(
                "Explicit translation failed",
                extra={"target_locale": target_locale},
            )
            return NLIP_Factory.create_text("Translation failed for the requested target locale.")

        try:
            logger.info("Falling back to agent-driven translation processing")
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
