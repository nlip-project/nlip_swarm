from __future__ import annotations
from typing import List
from typing import Any as NLIP_Message

class Agent:
    """
    Base Agent Class

    __init__()
    - name: The name of the agent
    - capabilities: List of tasks an agent can handle/complete
    - llm: Associated model of the agent

    handle(NLIP_Message) -> NLIP_Message
    - superclass should be implemented by actual agent class definition
    - defines how to handle an NLIP message

    """
    name: str
    capabilities: List[str]

    def __init__(self, name: str, capabilities: List[str], llm):
        self.name = name
        self.capabilities = capabilities
        self.llm = llm
    
    async def handle(self, message: NLIP_Message) -> NLIP_Message:
        raise NotImplementedError("This method should be implemented by subclasses.")