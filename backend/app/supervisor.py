import os
from typing import List

from langdetect import detect, LangDetectException

from .messages import NLIPMessage, NLIPResponse, NLIPSubMessage
from .agents.translation import OllamaTranslationAgent, TranslationError

PIVOT_LOCALE = os.getenv("NLIP_TRANSLATION_PIVOT_LOCALE", "en")
DEFAULT_SOURCE_LOCALE = os.getenv("NLIP_TRANSLATION_DEFAULT_LOCALE", "en")
_translator = OllamaTranslationAgent()


def process_nlip(payload: NLIPMessage) -> NLIPResponse:
    """
    Process an incoming NLIP message using a translate-to-English-then-back
    workflow so downstream agents can reason in a single language.
    """
    text_messages = [message for message in payload.messages if message.format == "text"]
    if not text_messages:
        return _empty_translation_response(payload)

    source_locale = _resolve_source_locale(payload, text_messages)
    pivot_messages = _translate_messages_to_pivot(text_messages, source_locale)
    processed_messages = _run_domain_logic(pivot_messages)
    final_messages = _translate_messages_to_source(processed_messages, source_locale)

    return NLIPResponse(
        id=payload.id,
        receiver=payload.sender,
        messages=final_messages,
    )


def _resolve_source_locale(payload: NLIPMessage, text_messages: List[NLIPSubMessage]) -> str:
    """
    Pick the locale used for responding. Prefer the payload locale, otherwise
    try to detect from the message content, and finally fall back to a default.
    """
    if payload.locale:
        return payload.locale

    detect_input = next((msg.content for msg in text_messages if msg.content.strip()), "")
    if detect_input:
        try:
            return detect(detect_input)
        except LangDetectException:
            pass

    return DEFAULT_SOURCE_LOCALE


def _translate_messages_to_pivot(messages: List[NLIPSubMessage], source_locale: str) -> List[str]:
    """
    Convert incoming user messages into the pivot language for downstream
    processing. Returns a list of pivot-language strings.
    """
    pivot_texts: List[str] = []
    for message in messages:
        content = message.content
        if source_locale == PIVOT_LOCALE:
            pivot_texts.append(content)
            continue
        try:
            pivot_texts.append(_translator.translate(content, PIVOT_LOCALE))
        except TranslationError as exc:
            pivot_texts.append(f"[translation-error] {exc}")
    return pivot_texts


def _run_domain_logic(messages_in_pivot: List[str]) -> List[str]:
    """
    Delegate to the downstream reasoning stack. For now we simply echo the
    translated text to keep the scaffold simple.
    """
    return messages_in_pivot


def _translate_messages_to_source(translated_messages: List[str], source_locale: str) -> List[NLIPSubMessage]:
    """
    Translate the pivot-language responses back into the user's locale.
    """
    final_messages: List[NLIPSubMessage] = []
    for text in translated_messages:
        if not text:
            continue
        if text.startswith("[translation-error]"):
            final_messages.append(
                NLIPSubMessage(
                    format="text",
                    content=text,
                    label="error",
                )
            )
            continue
        if source_locale == PIVOT_LOCALE:
            final_messages.append(
                NLIPSubMessage(
                    format="text",
                    content=text,
                    label=f"analysis:{source_locale}",
                )
            )
            continue
        try:
            localized_text = _translator.translate(text, source_locale)
        except TranslationError as exc:
            localized_text = f"Translation back to {source_locale} failed: {exc}"
            label = "error"
        else:
            label = f"analysis:{source_locale}"
        final_messages.append(
            NLIPSubMessage(
                format="text",
                content=localized_text,
                label=label,
            )
        )
    return final_messages


def _empty_translation_response(payload: NLIPMessage) -> NLIPResponse:
    """
    Provide a user-friendly error when there's nothing to translate.
    """
    return NLIPResponse(
        id=payload.id,
        receiver=payload.sender,
        messages=[
            NLIPSubMessage(
                format="text",
                content="No text messages were provided for translation.",
                label="error",
            )
        ],
    )
