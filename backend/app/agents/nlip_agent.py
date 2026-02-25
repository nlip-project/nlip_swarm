import asyncio
import logging
from typing import Callable, Optional
from .base import Agent, MODEL, API_BASE

logger = logging.getLogger("NLIP")

NLIP_INSTRUCTION = """
You are an NLIP Agent.

NLIP is an acronym for "Natural Language Interaction Protocol."  The NLIP project aims to define a protocol for the following use cases.
- Agent to Agent interactions in Natural Language
- User-Agent to Agent protocol

An NLIP Agent, when defined, is given a system instruction that describes its unique capabilities.

You may receive ORIGINAL_NLIP_JSON in system context.
When forwarding to other NLIP servers, always pass the FULL original NLIP JSON, not just text.

One of the first requests an NLIP Agent will be asked to fulfill is to describe its NLIP Capabilities.
When you are asked to describe your NLIP Capabilities, you should respond with a response of the format:
    AGENT:NAME
    CAPABILITY1:description, CAPABILITY2:description, CAPABILITY3:description, ...
- where NAME is your name
- CAPABILITITY1, CAPABILITY2 and CAPABILITY3 are dictionary keys.  The description associated with each should be unique.
- it is important that you include your NAME
- it is important that the capabilities are described in a means that another LLM can understand them

"""

class NlipAgent(Agent):
    def __init__(self,
                 name: str,
                 model: str = MODEL,
                instruction: Optional[str] = None,
                tools: Optional[list[Callable]] = None,
                api_base: Optional[str] = API_BASE):
        super().__init__(name, model, NLIP_INSTRUCTION, tools, api_base=api_base)

        if instruction:
            self.add_instruction(instruction)

