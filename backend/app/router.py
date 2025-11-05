from __future__ import annotations
import json
from .registry import AgentRegistry
from nlip_sdk.nlip import NLIP_Message
from typing import List, Optional, Callable
import re



def build_router_prompt(
    agent_names: List[str],
    task_text: str,
    subformat: Optional[str],
    history_text: str,
) -> str:
    return (
        "You are the NLIP router.\n"
        "Return STRICT JSON ONLY — no explanation outside the JSON.\n\n"
        "Format:\n"
        "{\n"
        "  \"agent_name\": \"<one_of_above>\",\n"
        "  \"reasoning\": \"short explanation\"\n"
        "}\n\n"
        f"agent_name MUST be one of: {', '.join(agent_names)}.\n"
        "Never invent new agent names.\n\n"
        f"CONVERSATION CONTEXT:\n{history_text}\n\n"
        f"TASK SUBFORMAT: {subformat}\n"
        f"TASK TEXT: {task_text}\n"
    )

def _extract_json_safely(text: str) -> dict:
    """
    Attempt to parse JSON from text without regex recursion.
    1) Try json.loads on the whole text.
    2) If that fails, scan for the first balanced JSON object and parse it.
       Handles quoted strings and escapes so braces inside strings are ignored.
    Returns a dict if a JSON object is found; otherwise {}.
    """
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    start_idx = None
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if start_idx is None:
            if ch == '{':
                start_idx = i
                depth = 1
                in_string = False
                escape = False
        else:
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and start_idx is not None:
                        candidate = text[start_idx:i+1]
                        try:
                            data = json.loads(candidate)
                            return data if isinstance(data, dict) else {}
                        except Exception:
                            start_idx = None
                            depth = 0
                            in_string = False
                            escape = False
    return {}

async def route(
    registry: AgentRegistry,
    subMessage: NLIP_Message,
    llm,
    build_prompt: Optional[Callable] = None,
    history_text: str = "",
    ):
    """
    params:
    - registry: AgentRegistry containing all available agents, list of agents
    - subMessage: NLIP_Message to be routed
    - llm: model used for routing decisions

    returns:
    - Agent selected to handle the subMessage

    Prompts the router LLM to select the best agent for the given subMessage.
    If only one candidate agent matches the subMessage, returns that agent directly.
    """
    subf = getattr(subMessage, "subformat", None)
    
    candidates = registry.match(subf)
    if candidates:
        if len(candidates) == 1:
            return candidates[0]
        agent_pool = candidates
    else:
        agent_pool = registry.agents
    
    agent_names = [a.name for a in agent_pool]
    prompt_builder = build_prompt or build_router_prompt
    sys_prompt = prompt_builder(
        agent_names=agent_names,
        task_text=str(getattr(subMessage, "content", "")),
        subformat=subf,
        history_text=history_text or ""
    )

    try:
        if hasattr(llm, "ainvoke"):
            raw_out = await llm.ainvoke(sys_prompt)
        else:
            raw_out = await llm.invoke(sys_prompt)
    except Exception:
        return agent_pool[0]

    raw_text = raw_out.content if hasattr(raw_out, "content") else str(raw_out)
    data = _extract_json_safely(raw_text)
    agent_name = data.get("agent_name") if isinstance(data, dict) else None

    if not agent_name or agent_name not in agent_names:
        retry_prompt = (
            sys_prompt
            + "\n\nREMINDER: Return STRICT JSON with exactly keys \"agent_name\" and \"reasoning\". No prose."
        )
        try:
            if hasattr(llm, "ainvoke"):
                raw_out2 = await llm.ainvoke(retry_prompt)
            else:
                raw_out2 = await llm.invoke(retry_prompt)
            raw_text2 = raw_out2.content if hasattr(raw_out2, "content") else str(raw_out2)
            data2 = _extract_json_safely(raw_text2)
            agent_name2 = data2.get("agent_name") if isinstance(data2, dict) else None
            agent_name = agent_name2 if agent_name2 in agent_names else None
        except Exception:
            agent_name = None

    if agent_name and agent_name in agent_names:
        for a in agent_pool:
            if a.name == agent_name:
                return a
    return agent_pool[0]
