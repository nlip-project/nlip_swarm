"""
Coordinator NLIP Agent

Per-session agent that discovers available NLIP agents from MOUNT_SPEC
and uses two tools to communicate:
 - connect_to_server(url)
 - send_to_server(url, message)

The coordinator learns agent NAME and capabilities by asking each URL
"What are your NLIP Capabilities?" and parsing the deterministic response:

AGENT:Name\n
CAP1:desc, CAP2:desc, ...
"""

import json
import os
import re
from typing import Optional, Any, Dict
from urllib.parse import urlparse

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from app._logging import logger
from app.agents.base import MODEL as DEFAULT_MODEL
from app.agents.nlip_agent import NlipAgent
from app.http_client.nlip_async_client import NlipAsyncClient
from app.system.config import MOUNT_URLS

sessions = {}

CAPABILITIES_QUERY = "what are your nlip capabilities?"
SOUND_URL = MOUNT_URLS.get("sound", "http://sound:8029")
TEXT_URL = MOUNT_URLS.get("text", "http://text:8027")
TRANSLATE_URL = MOUNT_URLS.get("translate", "http://translate:8026")
IMAGE_URL = MOUNT_URLS.get("image", "http://image:8028")
ENGLISH_LOCALES = {"en", "en-us", "en-gb"}
_LANG_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z]{2})?$")

_LOCALE_NAME_TO_CODE = {
    "english": "en",
    "inglés": "en",
    "ingles": "en",
    "spanish": "es",
    "español": "es",
    "espanol": "es",
    "french": "fr",
    "francés": "fr",
    "frances": "fr",
    "german": "de",
    "alemán": "de",
    "aleman": "de",
    "italian": "it",
    "italiano": "it",
    "portuguese": "pt",
    "portugués": "pt",
    "portugues": "pt",
    "chinese": "zh-cn",
    "chino": "zh-cn",
    "japanese": "ja",
    "japonés": "ja",
    "japones": "ja",
    "korean": "ko",
    "coreano": "ko",
}

_TRANSLATION_INTENT_PATTERNS = [
    re.compile(r"\btranslate\b", re.IGNORECASE),
    re.compile(r"\btranslation\b", re.IGNORECASE),
    re.compile(r"\btraduce\b", re.IGNORECASE),
    re.compile(r"\btraducir\b", re.IGNORECASE),
    re.compile(r"\btraduccion\b", re.IGNORECASE),
    re.compile(r"\btraducción\b", re.IGNORECASE),
]


def _is_translation_request(text: str) -> bool:
    if not text:
        return False
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) is not None for pattern in _TRANSLATION_INTENT_PATTERNS)


def _preview_text(text: str, limit: int = 120) -> str:
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def _is_capabilities_request(text: str) -> bool:
    if not text:
        return False

    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return False

    if normalized == CAPABILITIES_QUERY:
        return True

    return (
        "nlip" in normalized
        and "capabilit" in normalized
        and any(token in normalized for token in ("what", "describe", "list", "show"))
    )

_OLLAMA_URL   = os.getenv("OLLAMA_URL")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

if _OLLAMA_URL and _OLLAMA_MODEL:
    MODEL    = f"openai/{_OLLAMA_MODEL}"
    API_BASE = _OLLAMA_URL.rstrip("/")
else:
    MODEL    = DEFAULT_MODEL
    API_BASE = None


async def connect_to_server(url: str):
    """Connect to an NLIP server at the given URL."""
    try:
        parsed_url = urlparse(str(url))
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
    except Exception as e:
        return f"Exception: {e} testing"

    logger.debug(f"Parsed URL: {parsed_url}, scheme: {scheme}, netloc: {netloc}")
    if scheme not in {"http", "https", "mem"}:
        return f"Exception: Request URL has an unsupported protocol '{scheme}://'."
    if not netloc:
        return "Exception: Request URL is missing a host."

    allowed_urls = {f"{urlparse(v).scheme}://{urlparse(v).netloc}" for v in MOUNT_URLS.values()}
    hashkey = f"{scheme}://{netloc}"
    if hashkey not in allowed_urls:
        return f"Exception: Host '{hashkey}' is not in the allowed agent list."

    client = NlipAsyncClient.create_from_url(f"{scheme}://{netloc}/nlip")

    sessions[hashkey] = client

    logger.info(f"Saved {netloc} with client {client}")
    return f"Connected to {scheme}://{netloc}/"

async def send_to_server(url: str, message: str) -> dict:
    """Send a message to a connected NLIP server at the given URL and return the response."""
    parsed_url = urlparse(str(url))
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc

    hashkey = f"{scheme}://{netloc}"
    client = sessions.get(hashkey)
    if client is None:
        return {"error": f"Not connected to {hashkey}. Call connect_to_server first."}

    if isinstance(message, str):
        nlip_message = NLIP_Factory.create_text(message)
    elif isinstance(message, dict):
        if 'subformat' not in message and 'format' in message:
            message = message.copy()
            message['subformat'] = 'plain'
        nlip_message = NLIP_Message(**message)
    else:
        nlip_message = message

    logger.info(f"Sending message: {message}")
    nlip_response = await client.async_send(nlip_message)
    logger.info(f"Received response: {nlip_response.model_dump()}")

    return nlip_response.model_dump()


async def get_all_capabilities() -> Dict[str, Any]:
    """
    Query all currently connected NLIP servers with
    \"What are your NLIP Capabilities?\" and return a mapping from
    server URL to their reported capabilities text.
    """
    results: Dict[str, Any] = {}

    for hashkey, client in sessions.items():
        nlip_message = NLIP_Factory.create_text("What are your NLIP Capabilities?")
        try:
            nlip_response = await client.async_send(nlip_message)
            results[hashkey] = nlip_response.extract_text()
        except Exception as exc:
            logger.error(f"Failed to get capabilities from {hashkey}: {exc}")
            results[hashkey] = f"Error: {exc}"

    return results


def _session_key(url: str) -> str:
    parsed = urlparse(str(url))
    return f"{parsed.scheme}://{parsed.netloc}"


async def _ensure_connected(url: str) -> None:
    key = _session_key(url)
    if key in sessions:
        return

    result = await connect_to_server(url)
    if isinstance(result, str) and result.startswith("Exception:"):
        raise RuntimeError(result)


def _extract_response_text(response: Any) -> str:
    if isinstance(response, dict):
        content = response.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        for submsg in response.get("submessages") or []:
            if isinstance(submsg, dict):
                subcontent = submsg.get("content")
                if isinstance(subcontent, str) and subcontent.strip():
                    return subcontent.strip()
    if isinstance(response, str):
        return response.strip()
    return ""


def _extract_response_texts(response: Any) -> list[str]:
    if isinstance(response, dict):
        content = response.get("content")
        extras = []
        for submsg in response.get("submessages") or []:
            if isinstance(submsg, dict):
                extra = submsg.get("content")
                if isinstance(extra, str) and extra.strip() and extra != content:
                    extras.append(extra)

        if isinstance(content, str) and content.strip():
            return [content, *extras] if extras else [content]
    if isinstance(response, str) and response.strip():
        return [response]
    return [str(response)]


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
    return cleaned


def _is_english_locale(locale: Optional[str]) -> bool:
    if not locale:
        return False
    normalized = locale.strip().lower()
    return normalized in ENGLISH_LOCALES or normalized.startswith("en-")


def _normalize_locale(locale: Optional[str]) -> Optional[str]:
    if not locale:
        return None
    normalized = locale.strip().lower()
    if not normalized:
        return None
    return _LOCALE_NAME_TO_CODE.get(normalized, normalized)


def _extract_declared_locale(msg: NLIP_Message) -> Optional[str]:
    """Best-effort locale extraction from top-level or nested subformat fields."""
    try:
        msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg.model_dump()
    except Exception:
        return None

    def _get(entry, key):
        if isinstance(entry, dict):
            return entry.get(key)
        return getattr(entry, key, None)

    def _walk(entry) -> Optional[str]:
        subformat = _get(entry, "subformat")
        fmt = (_get(entry, "format") or "").lower()
        if isinstance(subformat, str) and (fmt.startswith("text") or fmt == ""):
            normalized = _normalize_locale(subformat)
            if normalized:
                return normalized

        for key in ("submessages", "messages"):
            children = _get(entry, key)
            if isinstance(children, list):
                for child in children:
                    found = _walk(child)
                    if found:
                        return found
        return None

    return _walk(msg_dict)


async def _detect_language_via_translation_server(text: str) -> Optional[str]:
    if not text or not text.strip():
        return None

    try:
        await _ensure_connected(TRANSLATE_URL)
        prompt = (
            "Detect the language of the text below. "
            "Return ONLY minified JSON with this exact shape: "
            "{\"language_code\":\"<iso-639-1-or-bcp-47-code>\"}.\n\n"
            f"Text:\n{text}"
        )
        response = await send_to_server(TRANSLATE_URL, prompt)
        raw = _strip_code_fence(_extract_response_text(response))
        if not raw:
            return None

        code: Optional[str] = None
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                value = payload.get("language_code")
                if isinstance(value, str):
                    code = value.strip().lower()
        except Exception:
            match = re.search(r"\b([a-z]{2,3}(?:-[a-z]{2})?)\b", raw.lower())
            if match:
                code = match.group(1)

        if code and _LANG_CODE_RE.match(code):
            return code
    except Exception as exc:
        logger.warning(f"Language detection failed via translation server: {exc}")

    return None


async def _translate_via_server(
    text: str,
    target_locale: str,
    source_locale: Optional[str] = None,
) -> Optional[str]:
    if not text or not text.strip():
        return None

    try:
        await _ensure_connected(TRANSLATE_URL)
        if source_locale:
            prompt = (
                "Translate the text below from "
                f"'{source_locale}' to '{target_locale}'. "
                "Return only the translated text with no explanation.\n\n"
                f"Text:\n{text}"
            )
        else:
            prompt = (
                f"Translate the text below to '{target_locale}'. "
                "Return only the translated text with no explanation.\n\n"
                f"Text:\n{text}"
            )

        response = await send_to_server(TRANSLATE_URL, prompt)
        translated = _extract_response_text(response)
        return translated.strip() if translated and translated.strip() else None
    except Exception as exc:
        logger.warning(f"Translation failed via translation server to {target_locale}: {exc}")
        return None


def inspect_message_formats(msg: NLIP_Message) -> dict:
    """
    Inspect NLIP message and return format information.

    Returns:
        dict with: 'formats', 'subformats', 'has_binary', 'has_image',
                   'has_audio', 'has_video'
    """
    formats = set()
    subformats = set()

    msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg.model_dump()

    def _get(entry, key):
        if isinstance(entry, dict):
            return entry.get(key)
        return getattr(entry, key, None)

    def _walk(entry) -> None:
        fmt = _get(entry, "format")
        if fmt:
            formats.add(fmt)
        sf = _get(entry, "subformat")
        if sf:
            subformats.add(sf)

        # NLIP SDKs sometimes use either "submessages" or "messages" for nested content.
        for key in ("submessages", "messages"):
            children = _get(entry, key)
            if isinstance(children, list):
                for child in children:
                    _walk(child)

    _walk(msg_dict)

    return {
        'formats': list(formats),
        'subformats': list(subformats),
        'has_binary': any('binary' in f.lower() for f in formats),
        'has_image': any('image' in sf.lower() for sf in subformats) or any('image' in f.lower() for f in formats),
        'has_audio': any('audio' in sf.lower() for sf in subformats) or any('audio' in f.lower() for f in formats),
    }


def extract_text_from_message(msg: NLIP_Message) -> str:
    """
    Extract text from NLIP payloads, including text/plain and nested messages.
    """
    try:
        text = (msg.extract_text() or "").strip()
        if text:
            return text
    except Exception:
        pass

    msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg.model_dump()

    def _get(entry, key):
        if isinstance(entry, dict):
            return entry.get(key)
        return getattr(entry, key, None)

    def _walk(entry) -> Optional[str]:
        fmt = (_get(entry, "format") or "").lower()
        content = _get(entry, "content")

        if isinstance(content, str) and content.strip():
            if fmt.startswith("text") or fmt == "":
                return content.strip()

        for key in ("submessages", "messages"):
            children = _get(entry, key)
            if isinstance(children, list):
                for child in children:
                    found = _walk(child)
                    if found:
                        return found
        return None

    extracted = _walk(msg_dict)
    return extracted or ""


async def route_by_format(message: dict) -> dict:
    """
    Route NLIP message based on format inspection.

    Args:
        message: NLIP message as dict

    Returns:
        dict with 'recommended_url', 'agent_name', 'confidence', 'reason'
    """
    nlip_msg = NLIP_Message(**message)
    format_info = inspect_message_formats(nlip_msg)

    if format_info['has_image']:
        return {
            'recommended_url': MOUNT_URLS.get('image', 'http://image:8028'),
            'agent_name': 'Image',
            'confidence': 'high',
            'reason': 'Message contains binary image data'
        }

    if format_info['has_audio']:
        return {
            'recommended_url': MOUNT_URLS.get('sound', 'http://sound:8029'),
            'agent_name': 'Sound',
            'confidence': 'high',
            'reason': 'Message contains binary audio data'
        }

    return {
        'recommended_url': None,
        'agent_name': None,
        'confidence': 'low',
        'reason': 'Text message - use LLM reasoning for routing'
    }


def extract_image_from_message(msg: NLIP_Message) -> Optional[str]:
    """Extract base64 image data from NLIP message."""
    msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg.model_dump()

    def _get(entry, key):
        if isinstance(entry, dict):
            return entry.get(key)
        return getattr(entry, key, None)

    def _maybe_image(entry) -> Optional[str]:
        content = _get(entry, "content") or ""
        if isinstance(content, str) and len(content) > 100:
            if content.startswith(("/9j/", "iVBORw0KG", "data:image")):
                return content
        for key in ("submessages", "messages"):
            submessages = _get(entry, key) or []
            if isinstance(submessages, list):
                for submsg in submessages:
                    subformat = (_get(submsg, 'subformat') or '').lower()
                    format_field = (_get(submsg, 'format') or '').lower()

                    if 'image' in subformat or 'image' in format_field:
                        content = _get(submsg, 'content') or ''
                        if isinstance(content, str) and len(content) > 100:
                            return content
                        # Recurse in case there are deeper nests
                        nested = _maybe_image(submsg)
                        if nested:
                            return nested
        return None

    return _maybe_image(msg_dict)


NLIP_COORDINATOR_PROMPT = """
You are the NLIP Coordinator Agent.

Your job is to route user requests to the correct NLIP server.

AVAILABLE SERVERS
These servers are already connected and ready to use:

- mem://basic      — general NLP tasks (entity recognition, sentiment analysis, etc.)
- http://translate:8026  — language translation
- http://text:8027       — text processing and manipulation
- http://sound:8029      — audio processing
- http://image:8028      — image recognition and processing

IMPORTANT RULES
- ONLY use the server URLs listed above.
- NEVER invent or guess new URLs.
- NEVER attempt to connect to external URLs.
- If a URL is not listed above, it is invalid.

HOW TO HANDLE REQUESTS

1. If the user asks for translation:
    → send the request to **http://translate:8026**

2. If the user asks for general NLP analysis:
   → send the request to **mem://basic**

3. If the user asks for text processing:
    → send the request to **http://text:8027**

4. If the user asks for audio processing:
    → send the request to **http://sound:8029**

5. If the user asks for image processing:
    → send the request to **http://image:8028**

TOOLS
You have three tools:

- send_to_server(url, message)
- get_all_capabilities()
- connect_to_server(url)

NORMAL OPERATION
All servers are already connected. You normally only need to call:

send_to_server

For non-English text requests, detect the source language, translate to English for processing, and translate the final answer back to the original language.

Only call connect_to_server if the user explicitly asks you to connect to a new server.

CAPABILITIES REQUEST
If the user asks:
"What are your NLIP Capabilities?"

You MUST:
1. Call get_all_capabilities
2. Summarize the capabilities returned for each server

TOOL USAGE RULES
- Call **only one tool per turn**
- Tool arguments must be JSON:
  {"url": "...", "message": "..."}

MEDIA / STRUCTURED PAYLOADS
If the incoming NLIP request contains structured or media data (images, audio, binary payloads), prefer using relay_nlip_to_server so the full payload is forwarded.

Use send_to_server only for simple text messages.
"""

class CoordinatorNlipAgent(NlipAgent):
    def __init__(self,
        name: str,
        model: Optional[str] = MODEL,
        instruction: Optional[str] = None,
        tools: Optional[list] = None,
        api_base: Optional[str] = API_BASE,
    ):
        if tools is None:
            tools = [connect_to_server, send_to_server, get_all_capabilities]
        super().__init__(name=name, model=model, tools=tools, api_base=api_base)

        self.add_instruction("You are an agent with tools for querying other NLIP Agent Servers.")
        self.add_instruction(NLIP_COORDINATOR_PROMPT)

        if instruction:
            self.add_instruction(instruction)

    async def process_nlip(self, nlip_msg) -> list[str]:
        """
        Override process_nlip to auto-route binary messages based on format.

        For messages with media (image/audio/video), routes to ALL relevant agents
        in parallel without LLM involvement. For text-only messages or complex
        queries, falls back to LLM-based routing.
        """
        logger.info(f"[{self.name}] Processing NLIP message")

        try:
            format_info = inspect_message_formats(nlip_msg)

            if format_info['has_image']:
                url = IMAGE_URL

                try:
                    await _ensure_connected(url)
                except Exception as e:
                    logger.error(f"[{self.name}] Failed to connect to {url}: {e}")
                    return [f"Error: Could not connect to image server: {e}"]

                nlip_dict = nlip_msg.to_dict() if hasattr(nlip_msg, 'to_dict') else nlip_msg.model_dump()

                try:
                    response = await send_to_server(url, nlip_dict)
                    if isinstance(response, dict) and 'content' in response:
                        return [response['content']]
                    return [str(response)]
                except Exception as exc:
                    logger.exception(f"[{self.name}] Error from image server: {exc}")
                    return [f"Error processing image: {exc}"]

            if format_info['has_audio']:
                url = SOUND_URL

                try:
                    await _ensure_connected(url)
                except Exception as e:
                    logger.error(f"[{self.name}] Failed to connect to {url}: {e}")
                    return [f"Error: Could not connect to sound server: {e}"]

                nlip_dict = nlip_msg.to_dict() if hasattr(nlip_msg, 'to_dict') else nlip_msg.model_dump()

                try:
                    response = await send_to_server(url, nlip_dict)
                    if isinstance(response, dict) and 'content' in response:
                        return [response['content']]
                    return [str(response)]
                except Exception as exc:
                    logger.exception(f"[{self.name}] Error from sound server: {exc}")
                    return [f"Error processing audio: {exc}"]

            text = extract_text_from_message(nlip_msg)

            if text:
                logger.info(
                    f"[{self.name}] Extracted text payload",
                    extra={
                        "text_len": len(text),
                        "text_preview": _preview_text(text),
                    },
                )

                if _is_capabilities_request(text):
                    logger.info(f"[{self.name}] Capabilities request detected; querying all connected agents")
                    capabilities = await get_all_capabilities()
                    lines = []
                    for url, summary in capabilities.items():
                        lines.append(f"{url}\n{summary}")
                    return ["\n\n".join(lines) if lines else "No connected agent capabilities available."]

                target_url = TEXT_URL
                explicit_translation_request = _is_translation_request(text)
                if explicit_translation_request:
                    target_url = TRANSLATE_URL
                    logger.info(
                        f"[{self.name}] Routing decision: translation",
                        extra={"target_url": target_url},
                    )
                else:
                    logger.info(
                        f"[{self.name}] Routing decision: text",
                        extra={"target_url": target_url},
                    )

                translated_input = text
                translate_back_to_locale: Optional[str] = None

                if not explicit_translation_request:
                    declared_locale = _normalize_locale(_extract_declared_locale(nlip_msg))
                    detected_locale = _normalize_locale(await _detect_language_via_translation_server(text))

                    source_locale = declared_locale
                    if detected_locale:
                        if not declared_locale or (_is_english_locale(declared_locale) and not _is_english_locale(detected_locale)):
                            source_locale = detected_locale

                    logger.info(
                        f"[{self.name}] Language resolution",
                        extra={
                            "declared_locale": declared_locale,
                            "detected_locale": detected_locale,
                            "resolved_source_locale": source_locale,
                        },
                    )

                    if source_locale and not _is_english_locale(source_locale):
                        english_text = await _translate_via_server(
                            text,
                            target_locale="en",
                            source_locale=source_locale,
                        )
                        if english_text and english_text.strip():
                            translated_input = english_text.strip()
                            translate_back_to_locale = source_locale
                            logger.info(
                                f"[{self.name}] Applied English pivot for multilingual request",
                                extra={"source_locale": source_locale},
                            )
                        else:
                            logger.warning(
                                f"[{self.name}] Failed to translate to English; using original text",
                                extra={"source_locale": source_locale},
                            )

                try:
                    await _ensure_connected(target_url)
                except Exception as exc:
                    logger.error(f"[{self.name}] Failed to connect to {target_url}: {exc}")
                    return [f"Error: Could not connect to {target_url}: {exc}"]

                try:
                    response = await send_to_server(target_url, translated_input)
                    outputs = _extract_response_texts(response)

                    if (
                        not explicit_translation_request
                        and translate_back_to_locale
                        and outputs
                    ):
                        translated_outputs: list[str] = []
                        for output in outputs:
                            back = await _translate_via_server(
                                output,
                                target_locale=translate_back_to_locale,
                                source_locale="en",
                            )
                            translated_outputs.append(back.strip() if back and back.strip() else output)
                        outputs = translated_outputs
                        logger.info(
                            f"[{self.name}] Translated response back to source locale",
                            extra={"target_locale": translate_back_to_locale},
                        )

                    logger.info(
                        f"[{self.name}] Downstream response received",
                        extra={
                            "target_url": target_url,
                            "outputs_count": len(outputs),
                            "first_output_preview": _preview_text(outputs[0] if outputs else ""),
                        },
                    )
                    return outputs
                except Exception as exc:
                    logger.exception(f"[{self.name}] Error routing text request to {target_url}: {exc}")
                    return [f"Error processing text request: {exc}"]

            return await super().process_nlip(nlip_msg)

        except Exception as e:
            logger.error(f"[{self.name}] Error in format-based routing: {e}", exc_info=True)
            return await super().process_nlip(nlip_msg)
