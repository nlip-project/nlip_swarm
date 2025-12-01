from app._logging import logger
import asyncio
import json
import litellm
from litellm import completion
from pydantic import TypeAdapter
import time
from typing import Any, Dict, List, Optional, cast, Callable
from dotenv import load_dotenv

#litellm._turn_on_debug() #pyright: ignore
load_dotenv()

#MODEL = "openai/gpt-4o-mini"
#MODEL = "ollama_chat/llama3.2:3b"
MODEL = "cerebras/llama3.3-70b"

# PROMPTS
TOOLS_INSTRUCTIONS = """
You are an agent with tools. When calling a tool, make sure to match the type signature of the tool.
"""

def schema_of(thing):
    adapter = TypeAdapter(thing)
    return adapter.json_schema()

class Agent:
    """
    Base Agent Class

    __init__()
    - name (str): The name of the agent
    - model (str): The LLM model being used
    - instruction (str): The system instructions
    - tools (list): the initial set of tools
    """
    def __init__(self, name: str, model: str = MODEL, instruction: Optional[str] = None, tools: Optional[list[Callable]] = None):
        self.tstart = time.time()
        self.name: str = name
        self.model: str = model
        self.instruction = instruction
        self.messages: List[Any] = [
            {
                "role": "system",
                "content": TOOLS_INSTRUCTIONS
            }
        ]
        self.add_instruction(f"Your NAME is {name}.")
        if instruction:
            self.add_instruction(instruction)

        self.tools: list[Dict] = []
        self.fnmap: Dict[str, Callable] = {}
        self.final_text: list[str] = []
        self._last_nlip_json: Optional[dict] = None

        for fn in (tools or []):
            self.add_tool(fn)

    def _trel(self):
        return time.time() - self.tstart

    def add_instruction(self, instruction: str):
        self.messages.append(
            {
                "role": "system",
                "content": instruction
            }
        )

    def add_tool(self, fn: Callable):
        name = fn.__name__

        self.tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": fn.__doc__,
                "parameters": schema_of(fn)
            }
        })
        self.fnmap[name] = fn

    def list_tools(self):
        return self.tools
    
    async def _call_tool(self, name: str, args: Dict, tool_call_id: str) -> bool:
        fn = self.fnmap.get(name)
        if not fn:
            logger.error(f"[{self.name}] Tool '{name}' not found in function map")
            return False
        
        if name == "send_to_server" and "message" not in args and self._last_nlip_json is not None:
            args["message"] = self._last_nlip_json

        logger.info(f"[{self.name}] Tool Call: {name}({args})")
        result = await fn(**args)
        content = result if isinstance(result, str) else json.dumps(result)
        logger.debug(f"[{self.name}] Tool '{name}' returned: {content[:200]}{'...' if len(str(content)) > 200 else ''}")
        self.messages.append(
            {
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": name,
                "content": content
            }
        )
        self.final_text.append(str(result))
        return True
    
    def _handle_response(self, response: Any):
        if getattr(response, "content", None):
            self.final_text.append(response.content)
        if getattr(response, "tool_calls", None):
            self.messages.append(response.model_dump())
        else:
            self.messages.append(response)


    async def _drive_llm(self) -> list[str]:
        response = cast(Any, completion(model=self.model, messages=self.messages, tools=self.tools))
        response_msg = response.choices[0].message
        if response_msg is None:
            raise RuntimeError("No Response from LLM")
        
        self._handle_response(response_msg)
        tool_calls = list(getattr(response_msg, "tool_calls", None) or [])

        while tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")
                await self._call_tool(tool_name, tool_args, tool_call.id)

            response = cast(Any, completion(model=self.model, messages=self.messages, tools=self.tools))
            response_msg = response.choices[0].message
            self._handle_response(response_msg)
            tool_calls = list(getattr(response_msg, "tool_calls", None) or [])

        return self.final_text

    async def process_query(self, query: str) -> list[str]:
        self.final_text = []
        self.messages.append({
            "role": "user",
            "content": query
        })
        return await self._drive_llm()
    
    async def process_nlip(self, nlip_msg: Any) -> list[str]:
        self.final_text = []

        try:
            nlip_json = nlip_msg.to_dict()
        except (AttributeError, TypeError):
            try:
                nlip_json = nlip_msg.model_dump()
            except (AttributeError, TypeError) as e:
                raise RuntimeError(f"Could not convert NLIP_Message to dict: {e}")
        self._last_nlip_json = nlip_json
        self.messages.append({
            "role": "user",
            "content": "ORIGINAL_NLIP_JSON:\n" +json.dumps(nlip_json, ensure_ascii=False)
        })

        text = ""
        try:
            text = nlip_msg.extract_text() or ""
        except (AttributeError, TypeError):
            pass
        user_text = text if text.strip() else "(no textual content in NLIP Message)"
        self.messages.append({
            "role": "user",
            "content": user_text
        })

        return await self._drive_llm()