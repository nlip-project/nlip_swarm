import os
from typing import List, Optional, Tuple, Dict, Any

from langdetect import detect, LangDetectException

from nlip_sdk import nlip
from .agents.translation import OllamaTranslationAgent, TranslationError
from .api import SafeApplication, NLIP_Session, setup_server

PIVOT_LOCALE = os.getenv("NLIP_TRANSLATION_PIVOT_LOCALE", "en")
DEFAULT_SOURCE_LOCALE = os.getenv("NLIP_TRANSLATION_DEFAULT_LOCALE", "en")
_translator = OllamaTranslationAgent()


def process_nlip(payload: nlip.NLIP_Message) -> nlip.NLIP_Message:
    """
    Process an incoming NLIP message using a translate-to-English-then-back
    workflow so downstream agents can reason in a single language.
    """
    text = _extract_text(payload)
    if not text or not text.strip():
        return nlip.NLIP_Factory.create_text("No text provided for translation.", language="english", label="error")
    
    source_lang, target_lang = _extract_languages(payload)
    if not source_lang:
        source_lang = _detect_safe(text)
    if not target_lang:
        target_lang = DEFAULT_SOURCE_LOCALE

    if not source_lang or not target_lang:
        return nlip.NLIP_Factory.create_text(
            "Could not determine source or target language.", language="english", label="error"
        )

    if _same_lang(source_lang, target_lang):
        translation = text
    else:
        try:
            translation = _translator.translate(text, target_lang)
        except TranslationError as exc:
            return nlip.NLIP_Factory.create_text(
                f"Translation failed: {exc}", language="english", label="error"
            )
        
    response = nlip.NLIP_Factory.create_text(
        translation, language=target_lang, label=f"translation:{target_lang}"
    )

    info = nlip.NLIP_SubMessage(
        format=nlip.AllowedFormats.generic,
        subformat="translation_info",
        content={
            "source_language": source_lang,
            "target_language": target_lang,
        },
        label="translation_info",
    )
    response.add_submessage(info)

    return response


def _resolve_source_locale(payload: nlip.NLIP_Message, text_messages: List[nlip.NLIP_SubMessage]) -> str:
    """
    Pick the locale used for responding. Prefer the payload locale, otherwise
    try to detect from the message content, and finally fall back to a default.
    """

    detect_input = next((msg.content for msg in text_messages if msg.content), "")
    if detect_input:
        try:
            return detect(detect_input)
        except LangDetectException:
            pass

    return DEFAULT_SOURCE_LOCALE

def _translate_messages_to_pivot(messages: List[nlip.NLIP_SubMessage], source_locale: str) -> List[str]:

    def _extract_submessage_text(content: Any) -> Optional[str]:
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, dict):
            for k in TEXT_KEYS:
                v = content.get(k)
                if isinstance(v, str) and v.strip():
                    return v
        return None

    pivot_texts: List[str] = []
    for message in messages:
        text = _extract_submessage_text(message.content)
        if not text:
            continue
        if source_locale == PIVOT_LOCALE:
            pivot_texts.append(text)
            continue
        try:
            pivot_texts.append(_translator.translate(text, PIVOT_LOCALE))
        except TranslationError as exc:
            pivot_texts.append(f"[translation-error] {exc}")
    return pivot_texts

def _run_domain_logic(messages_in_pivot: List[str]) -> List[str]:
    """
    Delegate to the downstream reasoning stack. For now we simply echo the
    translated text to keep the scaffold simple.
    """
    return messages_in_pivot


def _translate_messages_to_source(translated_messages: List[str], source_locale: str) -> List[nlip.NLIP_SubMessage]:
    """
    Translate the pivot-language responses back into the user's locale.
    """
    final_messages: List[nlip.NLIP_SubMessage] = []
    for text in translated_messages:
        if not text:
            continue
        if text.startswith("[translation-error]"):
            final_messages.append(
                nlip.NLIP_SubMessage(
                    format=nlip.AllowedFormats.text,
                    subformat="text",
                    content=text,
                    label="error",
                )
            )
            continue
        if source_locale == PIVOT_LOCALE:
            final_messages.append(
                nlip.NLIP_SubMessage(
                    format=nlip.AllowedFormats.text,
                    subformat="text",
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
            nlip.NLIP_SubMessage(
                format=nlip.AllowedFormats.text,
                subformat="text",
                content=localized_text,
                label=label,
            )
        )
    return final_messages

TEXT_KEYS = ("text", "content", "message", "body")

def _extract_text(message: nlip.NLIP_Message) -> Optional[str]:

    parts = []

    def pull_text(obj: Any) -> Optional[str]:
        if isinstance(obj, str) and obj.strip():
            return obj
        if isinstance(obj, dict):
            for k in TEXT_KEYS:
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    return v
        return None
    
    top = pull_text(message.content)
    if top:
        parts.append(top)
    
    for sub in (message.submessages or []):
        sub_text = pull_text(sub.content)
        if sub_text:
            parts.append(sub_text)

    return " ".join(parts) if parts else None

LANG_KEYS = {
    "source_language": ("source_language", "sourceLocale", "src_lang", "source"),
    "target_language": ("target_language", "targetLocale", "tgt_lang", "target"),
}

def _extract_languages(message: nlip.NLIP_Message) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(message.content, dict):
        source = message.content.get("source_language")
        target = message.content.get("target_language")
        if source or target:
            return source, target
        
    if message.submessages:
        for sub in message.submessages:
            if isinstance(sub.content, dict):
                source = _pick_language(sub.content, "source_language")
                target = _pick_language(sub.content, "target_language")
                if source or target:
                    return source, target
    return None, None

def _pick_language(d: Dict[str, Any], key: str) -> Optional[str]:
    for l in LANG_KEYS[key]:
        v = d.get(l)
        if isinstance(v, str) and v.strip():
            return v
    return None

def _detect_safe(text: str) -> Optional[str]:
    try:
        return detect(text)
    except LangDetectException:
        return None
    
def _same_lang(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b and a.lower() == b.lower())



class TranslationSession(NLIP_Session):
    async def execute(self, message: nlip.NLIP_Message) -> nlip.NLIP_Message:
        return process_nlip(message)
    
class TranslationApplication(SafeApplication):
    def create_session(self) -> NLIP_Session:
        s = TranslationSession()
        s.set_correlator()
        return s
app = setup_server(TranslationApplication())