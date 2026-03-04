from app._logging import logger
import json
import os
import litellm
from litellm import completion
from pydantic import TypeAdapter
import time
from typing import Any, Dict, List, Optional, cast, Callable
from dotenv import load_dotenv
from app.system.config import MODELS

#litellm._turn_on_debug() #pyright: ignore
load_dotenv()

# _OLLAMA_URL   = os.getenv("OLLAMA_URL")
# _OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
_OLLAMA_URL  = MODELS.get('ollama_url')
_OLLAMA_MODEL = MODELS.get('ollama_model')

if _OLLAMA_URL and _OLLAMA_MODEL:
    MODEL    = f"openai/{_OLLAMA_MODEL}"
    API_BASE: Optional[str] = _OLLAMA_URL.rstrip("/")
else:
    MODEL    = "cerebras/llama3.3-70b"
    API_BASE = None

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
    def __init__(self, name: str, model: str = MODEL, instruction: Optional[str] = None, tools: Optional[list[Callable]] = None, api_base: Optional[str] = API_BASE):
        self.tstart = time.time()
        self.name: str = name
        self.model: str = model
        self.api_base: Optional[str] = api_base
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
        self.tool_outputs: list[str] = []
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

        try:
            result = await fn(**args)
        except Exception as exc:
            logger.exception(f"[{self.name}] Tool '{name}' raised: {exc}")
            result = f"Error in tool '{name}': {exc}"

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
        self.tool_outputs.append(str(result))
        return True
    
    def _to_primitive(self, value: Any) -> Any:
        """
        Convert pydantic/BaseModel objects (and any nested collections)
        to plain Python types so they can be JSON-serialized.
        """
        if value is None:
            return None
        if hasattr(value, "model_dump_json"):
            try:
                return json.loads(cast(Any, value).model_dump_json())
            except Exception:
                pass
        if hasattr(value, "model_dump"):
            try:
                return cast(Any, value).model_dump()
            except Exception:
                pass
        if isinstance(value, dict):
            return {k: self._to_primitive(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._to_primitive(v) for v in value]
        return value

    def _serialize_assistant(self, response: Any) -> Dict[str, Any]:
        """
        Normalize assistant responses (with or without tool calls) into the
        wire format expected by OpenAI-style chat models.
        """
        if isinstance(response, dict):
            return cast(Dict[str, Any], self._to_primitive(response))

        msg: Dict[str, Any] = {
            "role": getattr(response, "role", None) or "assistant",
        }

        if hasattr(response, "content"):
            msg["content"] = self._to_primitive(getattr(response, "content"))

        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            msg["tool_calls"] = [self._to_primitive(tc) for tc in tool_calls]
        return cast(Dict[str, Any], self._to_primitive(msg))

    def _handle_response(self, response: Any):
        if getattr(response, "content", None):
            self.final_text.append(response.content)

        self.messages.append(self._serialize_assistant(response))


    async def _drive_llm(self) -> list[str]:
        response = cast(Any, completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            api_base=self.api_base,
        ))
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

            response = cast(Any, completion(
                model=self.model,
                messages=self.messages,
                tools=self.tools,
                api_base=self.api_base,
            ))
            response_msg = response.choices[0].message
            self._handle_response(response_msg)
            tool_calls = list(getattr(response_msg, "tool_calls", None) or [])

        return self.final_text + self.tool_outputs[-1:]

    async def process_query(self, query: str) -> list[str]:
        self.final_text = []
        self.tool_outputs = []
        self.messages.append({
            "role": "user",
            "content": query
        })
        return await self._drive_llm()
    
    async def process_nlip(self, nlip_msg: Any) -> list[str]:
        self.final_text = []
        self.tool_outputs = []

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
