import logging
from typing import Callable, Optional
from .base import Agent, MODEL, API_BASE

logger = logging.getLogger("NLIP")

NLIP_INSTRUCTION = """
You are an NLIP Agent.

NLIP stands for Natural Language Interaction Protocol.

NLIP allows:
- User ↔ Agent communication
- Agent ↔ Agent communication using natural language messages.

Your system instruction defines your capabilities.

CAPABILITY DISCOVERY

Agents may ask you:

"What are your NLIP Capabilities?"

When this happens, you MUST respond in the following format:

AGENT:NAME
CAPABILITY1:description
CAPABILITY2:description
CAPABILITY3:description

Rules:
- NAME must clearly identify the agent.
- Capabilities must be short and understandable by another LLM.
- Each capability should describe what tasks this agent can perform.

Example:

AGENT:TranslationAgent
TRANSLATE_TEXT:Translate text between languages
DETECT_LANGUAGE:Identify the language of a text
NORMALIZE_TEXT:Clean and normalize multilingual text

MESSAGE FORWARDING

You may receive ORIGINAL_NLIP_JSON in the system context.

If forwarding a request to another NLIP server:
- Always forward the **entire ORIGINAL_NLIP_JSON payload**
- Do not extract only the text unless explicitly instructed.

Your responses should be clear, structured, and machine-interpretable so that other agents can reason about your capabilities.

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

