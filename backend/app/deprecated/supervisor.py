import os
import json
from typing import List, Optional, Tuple, Dict, Any

from langdetect import detect, LangDetectException

from nlip_sdk import nlip
from ..agents.translation import OllamaTranslationAgent, TranslationError
from ..agents.imageRecognition import LlavaImageRecognitionAgent
from .api import SafeApplication, NLIP_Session, setup_server

PIVOT_LOCALE = os.getenv("NLIP_TRANSLATION_PIVOT_LOCALE", "en")
DEFAULT_SOURCE_LOCALE = os.getenv("NLIP_TRANSLATION_DEFAULT_LOCALE", "en")
_translator = OllamaTranslationAgent()
_image_agent = LlavaImageRecognitionAgent()

"""
Actual message parsing logic.
"""


def process_nlip(payload: nlip.NLIP_Message) -> nlip.NLIP_Message:
    """
    Process an incoming NLIP message using a translate-to-English-then-back
    workflow so downstream agents can reason in a single language.
    """
    # If the incoming message contains image(s), use the image processing flow
    #if _message_contains_image(payload):
    #    return _process_image_payload(payload)

    # Otherwise fall back to text-only translate flow
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

"""
Ben I don't know what these function are for so I want you to look at them.
"""

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

"""
Helper functions for pulling the actual content from an NLIP message,
recognizing languages, and for processing a request.
"""

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

    # Check top-level content first. If the message itself is an image, describe it.
    top_text = pull_text(message.content)
    if top_text:
        parts.append(top_text)
    else:
        # top-level might be binary (image) format per NLIP AllowedFormats
        fmt = getattr(message, "format", None)
        if fmt == nlip.AllowedFormats.binary or (isinstance(fmt, str) and fmt.lower() == "binary"):
            desc = None
            # desc = _describe_image_from_content(message.content)
            if desc:
                parts.append(desc)

    # Now handle submessages: text submessages and image submessages
    for sub in (message.submessages or []):
        sub_text = pull_text(sub.content)
        if sub_text:
            parts.append(sub_text)
            continue
        sub_fmt = getattr(sub, "format", None)
        if sub_fmt == nlip.AllowedFormats.binary or (isinstance(sub_fmt, str) and sub_fmt.lower() == "binary"):
            desc = None
            # desc = _describe_image_from_content(sub.content)
            if desc:
                parts.append(desc)

    return " ".join(parts) if parts else None


def _message_contains_image(message: nlip.NLIP_Message) -> bool:
    """Return True if the NLIP message or any submessage is a binary image."""
    # top-level
    fmt = getattr(message, "format", None)
    subf = getattr(message, "subformat", None)
    if (fmt == nlip.AllowedFormats.binary or (isinstance(fmt, str) and fmt.lower() == "binary")) and isinstance(subf, str) and subf.lower().startswith("image"):
        return True

    # submessages
    for sub in (message.submessages or []):
        sf = getattr(sub, "format", None)
        ssubf = getattr(sub, "subformat", None)
        if (sf == nlip.AllowedFormats.binary or (isinstance(sf, str) and sf.lower() == "binary")) and isinstance(ssubf, str) and ssubf.lower().startswith("image"):
            return True
    return False


def _get_encoded_from_content(img_content: Any) -> Optional[str]:
    """Extract base64-encoded image string from content which may be a string or dict."""
    if isinstance(img_content, str) and img_content.strip():
        return img_content
    if isinstance(img_content, dict):
        for k in ("data", "image", "content", "b64", "base64"):
            v = img_content.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return None


def _process_image_payload(message: nlip.NLIP_Message) -> nlip.NLIP_Message:
    """Process messages that include image binary payloads.

    For each image, call the image agent with an optional translated prompt.
    Return a NLIP_Message containing structured results and a human-readable analysis.
    """
    # Determine prompt/instruction (prefer labeled prompt)
    prompt_text = None
    structured_instruction = None
    for sub in (message.submessages or []):
        if getattr(sub, "label", None) and sub.label and sub.label.lower() in ("prompt") and sub.format == nlip.AllowedFormats.text:
            prompt_text = sub.content
            break
    # fallback: first text submessage
    if not prompt_text:
        for sub in (message.submessages or []):
            if sub.format == nlip.AllowedFormats.text:
                prompt_text = sub.content
                break
    # structured instruction fallback
    if not prompt_text:
        for sub in (message.submessages or []):
            if sub.format == nlip.AllowedFormats.structured:
                structured_instruction = sub.content
                break

    source_lang, target_lang = _extract_languages(message)
    if not source_lang:
        if prompt_text:
            source_lang = _detect_safe(prompt_text)
        else:
            source_lang = DEFAULT_SOURCE_LOCALE

    # prepare prompt for agent in pivot language
    agent_prompt = None
    if structured_instruction is not None:
        # serialize structured instruction for models that accept textual prompts
        agent_prompt = json.dumps(structured_instruction)
    elif prompt_text:
        if source_lang == PIVOT_LOCALE:
            agent_prompt = prompt_text
        else:
            try:
                agent_prompt = _translator.translate(prompt_text, PIVOT_LOCALE)
            except TranslationError:
                agent_prompt = prompt_text

    # create a response container (use generic text message as wrapper)
    resp = nlip.NLIP_Factory.create_generic("", "image_result")

    # iterate images: include top-level image as an item first
    images: List[Tuple[str, str]] = []  # list of (label, encoded)
    if (getattr(message, "format", None) == nlip.AllowedFormats.binary or (isinstance(getattr(message, "format", None), str) and getattr(message, "format", None).lower() == "binary")) and isinstance(getattr(message, "subformat", None), str) and getattr(message, "subformat", None).lower().startswith("image"):
        enc = _get_encoded_from_content(message.content)
        if enc:
            images.append((getattr(message, "label", "image"), enc))

    for sub in (message.submessages or []):
        sf = getattr(sub, "format", None)
        ssubf = getattr(sub, "subformat", None)
        if (sf == nlip.AllowedFormats.binary or (isinstance(sf, str) and sf.lower() == "binary")) and isinstance(ssubf, str) and ssubf.lower().startswith("image"):
            enc = _get_encoded_from_content(sub.content)
            if enc:
                images.append((getattr(sub, "label", "image"), enc))

    if not images:
        return nlip.NLIP_Factory.create_text("No image payloads found.", language="english", label="error")

    # For each image, call the agent and add structured/text results
    for lbl, enc in images:
        try:
            result = _image_agent.recognize_image(enc, prompt=agent_prompt)
        except Exception as exc:
            resp.add_submessage(
                nlip.NLIP_SubMessage(
                    format=nlip.AllowedFormats.error,
                    subformat="text",
                    content=f"Image recognition failed: {exc}",
                    label="error",
                )
            )
            continue

        # If agent returned dict-like structured result, attach as structured submessage
        if isinstance(result, dict):
            # Optionally translate textual fields inside the dict back to the source language.
            # For simplicity, keep structured result as-is, and also attach a human-readable text if available.
            struct_sub = nlip.NLIP_SubMessage(
                format=nlip.AllowedFormats.structured,
                subformat="result",
                content=result,
                label=f"analysis:{source_lang}",
            )
            resp.add_submessage(struct_sub)

            # extract any textual explanation
            text_rep = None
            for k in ("response", "text", "description", "output"):
                v = result.get(k)
                if isinstance(v, str) and v.strip():
                    text_rep = v
                    break
            if not text_rep:
                # try first choice
                choices = result.get("choices") or result.get("outputs")
                if isinstance(choices, (list, tuple)) and choices:
                    first = choices[0]
                    if isinstance(first, dict):
                        for k in ("text", "output", "content"):
                            v = first.get(k)
                            if isinstance(v, str) and v.strip():
                                text_rep = v
                                break
                    elif isinstance(first, str):
                        text_rep = first

            if text_rep:
                # translate back from pivot if needed
                if source_lang != PIVOT_LOCALE:
                    try:
                        text_rep = _translator.translate(text_rep, source_lang)
                    except TranslationError:
                        pass
                resp.add_submessage(
                    nlip.NLIP_SubMessage(
                        format=nlip.AllowedFormats.text,
                        subformat=source_lang,
                        content=text_rep,
                        label=f"analysis:{source_lang}",
                    )
                )

        else:
            # treat as plain text
            text_out = str(result)
            if source_lang != PIVOT_LOCALE:
                try:
                    text_out = _translator.translate(text_out, source_lang)
                except TranslationError:
                    pass
            resp.add_submessage(
                nlip.NLIP_SubMessage(
                    format=nlip.AllowedFormats.text,
                    subformat=source_lang,
                    content=text_out,
                    label=f"analysis:{source_lang}",
                )
            )

    # attach translation info
    info = nlip.NLIP_SubMessage(
        format=nlip.AllowedFormats.generic,
        subformat="translation_info",
        content={"source_language": source_lang, "target_language": PIVOT_LOCALE},
        label="translation_info",
    )
    resp.add_submessage(info)

    return resp

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
    for lang_key in LANG_KEYS[key]:
        v = d.get(lang_key)
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

"""
Actual Application and Session classes for NLIP server.
Might have a more generic architecture in future, 
to making switching models/using multiple models is better.
"""
class TranslationSession(NLIP_Session):
    async def execute(self, message: nlip.NLIP_Message) -> nlip.NLIP_Message:
        return process_nlip(message)
    
class TranslationApplication(SafeApplication):
    def create_session(self) -> NLIP_Session:
        s = TranslationSession()
        s.set_correlator()
        return s
app = setup_server(TranslationApplication())

