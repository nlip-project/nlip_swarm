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

import asyncio
import logging
import os
from typing import Optional, Any, Dict
from urllib.parse import urlparse
import httpx
import json

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from app.agents.base import MODEL as DEFAULT_MODEL
from app.agents.nlip_agent import NlipAgent
from app.http_client.nlip_async_client import NlipAsyncClient
from app.agents.imageRecognition import describe_image

sessions = {}
from app._logging import logger

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

    client = NlipAsyncClient.create_from_url(f"{scheme}://{netloc}/nlip")

    hashkey = f"{scheme}://{netloc}"
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
            'recommended_url': 'mem://image',
            'agent_name': 'Image',
            'confidence': 'high',
            'reason': 'Message contains binary image data'
        }

    if format_info['has_audio']:
        return {
            'recommended_url': 'mem://sound',
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
- mem://translate  — language translation
- mem://text       — text processing and manipulation
- mem://sound      — audio processing
- mem://image      — image recognition and processing

IMPORTANT RULES
- ONLY use the server URLs listed above.
- NEVER invent or guess new URLs.
- NEVER attempt to connect to external URLs.
- If a URL is not listed above, it is invalid.

HOW TO HANDLE REQUESTS

1. If the user asks for translation:
   → send the request to **mem://translate**

2. If the user asks for general NLP analysis:
   → send the request to **mem://basic**

3. If the user asks for text processing:
   → send the request to **mem://text**

4. If the user asks for audio processing:
   → send the request to **mem://sound**

5. If the user asks for image processing:
   → send the request to **mem://image**

TOOLS
You have three tools:

- send_to_server(url, message)
- get_all_capabilities()
- connect_to_server(url)

NORMAL OPERATION
All servers are already connected. You normally only need to call:

send_to_server

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
        model: str = MODEL,
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
                image_data = extract_image_from_message(nlip_msg)

                if not image_data:
                    logger.warning(f"[{self.name}] Image format detected but no image data found")
                    return ["No image data found in message"]

                try:
                    text_prompt = nlip_msg.extract_text()
                except Exception:
                    text_prompt = None

                try:
                    result = await describe_image(image_data, text_prompt)
                    return [result]
                except Exception as exc:
                    logger.exception(f"[{self.name}] Error calling describe_image: {exc}")
                    return [f"Error processing image: {exc}"]

            if format_info['has_audio']:
                url = 'mem://sound'

                if url not in sessions:
                    try:
                        await connect_to_server(url)
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

            return await super().process_nlip(nlip_msg)

        except Exception as e:
            logger.error(f"[{self.name}] Error in format-based routing: {e}", exc_info=True)
            return await super().process_nlip(nlip_msg)
