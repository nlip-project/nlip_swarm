from __future__ import annotations

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
from typing import Optional, Any
from urllib.parse import urlparse
import httpx
import json
from pydantic import AnyHttpUrl

from nlip_sdk.nlip import NLIP_Factory
from app.agents.nlip_agent import NlipAgent
from app.http_client.nlip_async_client import NlipAsyncClient

sessions = {}

logger = logging.getLogger("NLIP")
#MODEL = "openai/gpt-4o-mini"
#MODEL = "ollama_chat/llama3.2:3b"
MODEL = "cerebras/llama3.3-70b"

async def connect_to_server(url: AnyHttpUrl):
    try:
        parsed_url = urlparse(str(url))
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
    except Exception as e:
        return f"Exception: {e}"
    
    await asyncio.sleep(1.0)
    client = NlipAsyncClient.create_from_url(f"{scheme}://{netloc}/nlip")

    hashkey = f"{scheme}://{netloc}"
    sessions[hashkey] = client

    logger.info(f"Saved {netloc} with client {client}")
    return f"Connected to {scheme}://{netloc}/"

async def send_to_server(url: AnyHttpUrl, message: str) -> dict:
    parsed_url = urlparse(str(url))
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    
    hashkey = f"{scheme}://{netloc}"
    client = sessions[hashkey]

    nlip_message = NLIP_Factory.create_text(message)
    logger.info(f"Sending message: {message}")
    nlip_response = await client.async_send(nlip_message)
    logger.info(f"Received response: {nlip_response.model_dump()}")

    return nlip_response.extract_text()

NLIP_COORDINATOR_PROMPT = """
You are an advanced NLIP Agent with the capability to speak to other NLIP Agents.
You have two tools for this purpose:
- connect_to_server
- send_to_server

When you are asked to connect to a server at a specific URL, use the connect_to_server tool with that URL to establish a connection.
If the response to that tool begins with: "Connected to ", then the connection is valid.  Otherwise, it is not.
For a valid connection, you should follow the connect_to_server tool call with a tool call of send_to_server to the same URL with the string: "What are your NLIP Capabilities?"
The remote Agent will respond with its [NAME] and capabilities.  Take note of this information, especially the NAME.  In future requests, if a user asks for you to send a request to NAME you should use the send_to_server tool with the URL that was associated with NAME and use the request as the msg: argument.
"""

class CoordinatorNlipAgent(NlipAgent):
    def __init__(self,
        name: str,
        model: str = MODEL,
        instruction: Optional[str] = None,
        tools = [connect_to_server, send_to_server],
    ):
        super().__init__(name=name, model=model, tools=tools)

        self.add_instruction("You are an agent with tools for querying other NLIP Agent Servers.")
        self.add_instruction(NLIP_COORDINATOR_PROMPT)

        if instruction:
            self.add_instruction(instruction)