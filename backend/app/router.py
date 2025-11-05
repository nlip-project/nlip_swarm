from __future__ import annotations
import json
from .registry import AgentRegistry
from nlip_sdk.nlip import NLIP_Message
from .agents.base import Agent
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

def _extract_json_safetly(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{(?:[^{}]|(?R))*\}", text, flags=re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
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
        if len(candidates) > 1:
            chosen = candidates[0]
        return chosen
    
    agent_names = [a.name for a in registry.agents]
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
    except Exception as e:
        fallback = registry.agents[0]
        return fallback
    
    if hasattr(raw_out, "content"):
        raw_text = raw_out.content
    else:
        raw_text = str(raw_out)

    data = _extract_json_safetly(raw_text)
    agent_name = data.get("agent_name")

    if not agent_name or agent_name not in agent_names:
        fallback = registry.agents[0]
        return fallback
    for a in registry.agents:
        if a.name == agent_name:
            return a
    fallback = registry.agents[0]
    return fallback