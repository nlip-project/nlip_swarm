import asyncio
import logging
import json
from pydantic import TypeAdapter
import time
from typing import Any, Dict, List, Optional, cast
from typing import Callable

def schema_of(thing):
    adapter = TypeAdapter(thing)
    return adapter.json_schema()

from litellm import completion
from dotenv import load_dotenv

import litellm
#litellm._turn_on_debug() #pyright: ignore


load_dotenv()
#MODEL = "openai/gpt-4o-mini"
#MODEL = "ollama_chat/llama3.2:3b"
MODEL = "cerebras/llama3.3-70b"

# PROMPTS
TOOLS_INSTRUCTIONS = """
You are an agent with tools. When calling a tool, make sure to match the type signature of the tool.
"""

class Agent:
    """
    Base Agent Class

    __init__()
    - name (str): The name of the agent
    - model (str): The LLM model being used
    - instruction (str): The system instructions
    - tools (list): the initial set of tools
    """
    def __init__(self, name: str, model: str = MODEL, instruction: Optional[str] = None, tools: list[Callable] = []):
        self.tstart = time.time()
        self.name: str = name
        self.model: str = model
        self.instruction: Optional[str] = instruction

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
        isFound = False

        fn = self.fnmap[name]
        if fn:
            isFound = True
            result = await fn(**args)
            self.final_text.append(f"Calling tool:{name} with args:{args}")

            content = result
            if type(content) != str:
                content = json.dumps(content)

            self.messages.append(
                {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": name,
                    "content": content
                }
            )
        return isFound
    
    def _handle_response(self, response):

        if response.content is not None:
            self.final_text.append(response.content)
        
        tools_calls = response.tool_calls

        if tools_calls:
            self.messages.append(response.model_dump())
        else:
            self.messages.append(response)

    async def process_query(self, query: str) -> list[str]:
        print(f"Processing query")

        self.final_text = []
        self.messages.append({"role": "user", "content": query})

        response = cast(Any, completion(
            model=self.model, messages=self.messages, tools=self.tools
        ))

        response_message = cast(Any, response).choices[0].message

        if response_message is None:
            import sys
            print(f"RESPONSE:{response_message}")
            sys.exit(1)

        self._handle_response(response_message)
        tool_calls = list(response_message.tool_calls or [])

        while tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_call_id = tool_call.id

                if await self._call_tool(tool_name, tool_args, tool_call_id) == False:
                    self.messages.append({"role": "user", "content": f"Tool '{tool_name}' not found."})

            response = cast(Any, completion(
                model=self.model, messages=self.messages, tools=self.tools
            ))
            response_message = cast(Any, response).choices[0].message
            self._handle_response(response_message)
            tool_calls = list(response_message.tool_calls or [])
        
        return self.final_text
