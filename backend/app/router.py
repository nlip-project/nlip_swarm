from __future__ import annotations
import json
from .registry import AgentRegistry
from nlip_sdk.nlip import NLIP_Message
from .agents.base import Agent

ROUTER_SYS = (
    "You are the NLIP router. Return STRICT JSON: {{\"agent_name\": <one_of>, \"reasoning\": \"...\"}}."
    "agent_name MUST be one of: {agent_names}. Never invent names."
)

def _extract_json_safetly(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in the text.")
    return json.loads(text[start:end+1])

async def route(registry: AgentRegistry, subMessage: NLIP_Message, llm) -> "Agent":
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

    candidates = registry.match(getattr(subMessage, "content", None))
    if len(candidates) == 1:
        return candidates[0]
    
    agent_names = [a.name for a in registry.agents]
    prompt = [
        ("system", ROUTER_SYS.format(agent_names=agent_names)),
        (
            "user",
            f"Task: {getattr(subMessage, 'content', '')} Subformat: {getattr(subMessage, 'subformat', None)} Agents: {agent_names}",
        ),
    ]
    try:
        out = llm.invoke(prompt)
        text = out if isinstance(out, str) else getattr(out, "content", str(out))
        data = _extract_json_safetly(text)
        name = data.get("agent_name")
        for a in registry.agents:
            if a.name == name:
                return a
    except Exception:
        pass
    
    return candidates[0] if candidates else registry.agents[0]