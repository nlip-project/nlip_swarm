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

from typing import Optional, Any, Dict
from urllib.parse import urlparse
from app._logging import logger

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message
from app.agents.nlip_agent import NlipAgent
from app.http_client.nlip_async_client import NlipAsyncClient
from app.agents.imageRecognition import describe_image
from app.system.config import MODELS

sessions = {}


#MODEL = "openai/gpt-4o-mini"
#MODEL = "ollama_chat/llama3.2:3b"
# MODEL = "cerebras/llama3.3-70b"
MODEL = MODELS.get('coordinator_model', 'cerebras/llama3.3-70b')


async def connect_to_server(url: str):
    try:
        parsed_url = urlparse(str(url))
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
    except Exception as e:
        return f"Exception: {e} testing"

    logger.debug(f"Parsed URL: {parsed_url}, scheme: {scheme}, netloc: {netloc}")
    client = NlipAsyncClient.create_from_url(f"{scheme}://{netloc}/nlip")

    hashkey = f"{scheme}://{netloc}"
    sessions[hashkey] = client

    logger.info(f"Saved {netloc} with client {client}")
    return f"Connected to {scheme}://{netloc}/"

async def send_to_server(url: str, message: str) -> dict:
    parsed_url = urlparse(str(url))
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc

    hashkey = f"{scheme}://{netloc}"
    client = sessions[hashkey]

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

    if 'format' in msg_dict:
        formats.add(msg_dict['format'])
    if 'subformat' in msg_dict:
        subformats.add(msg_dict['subformat'])

    if 'submessages' in msg_dict and isinstance(msg_dict['submessages'], list):
        for submsg in msg_dict['submessages']:
            if 'format' in submsg:
                formats.add(submsg['format'])
            if 'subformat' in submsg:
                subformats.add(submsg['subformat'])

    return {
        'formats': list(formats),
        'subformats': list(subformats),
        'has_binary': 'binary' in formats,
        'has_image': any('image' in sf for sf in subformats),
        'has_audio': any('audio' in sf for sf in subformats),
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

    content = msg_dict.get('content', '')
    if content and isinstance(content, str) and len(content) > 500:
        if content.startswith(('/9j/', 'iVBORw0KG', 'data:image')):
            return content

    submessages = msg_dict.get('submessages', [])
    if isinstance(submessages, list):
        for submsg in submessages:
            subformat = submsg.get('subformat', '').lower()
            format_field = submsg.get('format', '').lower()

            if 'image' in subformat or 'image' in format_field:
                content = submsg.get('content', '')
                if content and isinstance(content, str) and len(content) > 100:
                    return content

    return None


NLIP_COORDINATOR_PROMPT = """
You are an advanced NLIP Agent with the capability to speak to other NLIP Agents.
You have three tools for this purpose:
- connect_to_server
- send_to_server
- get_all_capabilities

When you are asked to connect to a server at a specific URL, use the connect_to_server tool with that URL to establish a connection.
If the response to that tool begins with: "Connected to ", then the connection is valid.  Otherwise, it is not.
For a valid connection, you should follow the connect_to_server tool call with a tool call of send_to_server to the same URL with the string: "What are your NLIP Capabilities?"
The remote Agent will respond with its [NAME] and capabilities.  Take note of this information, especially the NAME.  In future requests, if a user asks for you to send a request to NAME you should use the send_to_server tool with the URL that was associated with NAME and use the request as the msg: argument.

If the user asks you: "What are your NLIP Capabilities?" you MUST call the get_all_capabilities tool first to gather capabilities for all connected servers, then summarize those capabilities in your final natural-language response. Separate the capabilities of each server clearly by server URL.

When the incoming NLIP message includes media/structured content (e.g., binary/image/audio/video or other submessages), prefer relay_nlip_to_server so downstream agents receive the full payload. Use send_to_server only for simple text-only interactions.

Tool calling rules:
- Call at most ONE tool per turn. If multiple steps are needed (e.g., connect, then send), do them sequentially across turns.
- Pass tool arguments as a JSON object with named keys, e.g., {"url": "...", "message": "..."}.
"""

class CoordinatorNlipAgent(NlipAgent):
    def __init__(self,
        name: str,
        model: str = MODEL,
        instruction: Optional[str] = None,
        tools: Optional[list] = None,
    ):
        if tools is None:
            tools = [connect_to_server, send_to_server, get_all_capabilities]
        super().__init__(name=name, model=model, tools=tools)

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
                logger.info(f"[{self.name}] Image detected, calling describe_image directly")

                image_data = extract_image_from_message(nlip_msg)

                if not image_data:
                    logger.warning(f"[{self.name}] Image format detected but no image data found")
                    return ["No image data found in message"]

                try:
                    text_prompt = nlip_msg.extract_text()
                except Exception:
                    text_prompt = None

                try:
                    logger.info(f"[{self.name}] Calling describe_image with image data length: {len(image_data)}")
                    result = await describe_image(image_data, text_prompt)
                    logger.info(f"[{self.name}] describe_image returned: {result[:100]}...")
                    return [result]
                except Exception as exc:
                    logger.exception(f"[{self.name}] Error calling describe_image: {exc}")
                    return [f"Error processing image: {exc}"]

            if format_info['has_audio']:
                logger.info(f"[{self.name}] Audio detected, routing to sound server")
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

            logger.info(f"[{self.name}] No media detected, using LLM routing")
            return await super().process_nlip(nlip_msg)

        except Exception as e:
            logger.error(f"[{self.name}] Error in format-based routing: {e}", exc_info=True)
            return await super().process_nlip(nlip_msg)