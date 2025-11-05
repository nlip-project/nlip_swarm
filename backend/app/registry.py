from __future__ import annotations
from typing import Dict, List
from .agents.base import Agent

class AgentRegistry:
    """
    Agent Registry Class

    __init__(self, agents: List[Agent])
    - agents: List of Agents that can be used by the Swarm Manager.
    - cap_index: Internal index mapping capabilities to agents.

    match(self, subformat: str | None)
    - subformat: The subformat string to match against agent capabilities.
    - Returns a list of agents that match the given subformat.

    """
    def __init__(self, agents: List[Agent]):
        self.agents = agents
        self.cap_index: Dict[str, List[Agent]] = {}
        for a in agents:
            for cap in a.capabilities:
                self.cap_index.setdefault(cap, []).append(a)

    def match(self, subformat: str | None) -> List[Agent]:
        if subformat and subformat in self.cap_index:
            return self.cap_index[subformat]
        if subformat and "." in subformat:
            prefix = subformat.split(".", 1)[0] + "."
            return self.cap_index.get(prefix, [])
        return []