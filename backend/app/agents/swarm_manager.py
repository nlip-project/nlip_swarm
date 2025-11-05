from __future__ import annotations
import asyncio
from typing import List, cast
from .base import Agent
from ..registry import AgentRegistry
from ..router import route
from nlip_sdk.nlip import NLIP_Message, NLIP_Factory, AllowedFormats, NLIP_SubMessage

class SwarmManager(Agent):
    """
    Swarm Manager Agent Class

    __init__(registry: AgentRegistry, router_llm)
    - registry: The AgentRegistry containing all available agents, list of agents
    - router_llm: The model used for routing decisions by the swarm manager

    dispath(subMessage: NLIP_Message) -> NLIP_Message
    - subMessage: NLIP_Message to be dispatched to an agent

    routes the subMessage to the appropriate agent and returns its response

    handle(message: NLIP_Message) -> NLIP_Message
    - message: Top-level NLIP_Message containing submessages or single message

    routes the message to the appropriate agent and returns its response
    """
    def __init__(self, registry: AgentRegistry, router_llm):
        super().__init__(name="swarm_manager", capabilities=["swarm.manage", "plan.dispatch"], llm=router_llm)
        self.registry = registry
        self.router_llm = router_llm

    async def dispatch(self, subMessage: NLIP_Message) -> NLIP_Message:
        agent = await route(self.registry, subMessage, self.router_llm)
        try:
            return await agent.handle(subMessage)
        except Exception as e:
            err = NLIP_Factory.create_text(f"Agent {agent.name} failed: {repr(e)}", label=getattr(subMessage, "label", ''))
            err.messagetype = "error"
            return err
        

    async def handle(self, message: NLIP_Message) -> NLIP_Message:
        """
        Receive a top-level NLIP request, fan out to agents, and return a bundled response.
        Ensures all `submessages` we create are proper NLIP_SubMessage instances (format is AllowedFormats).
        """

        if getattr(message, "submessages", None):
            incoming_subs: list[NLIP_SubMessage] = message.submessages  # type: ignore[assignment]
        else:
            incoming_subs = [
                NLIP_SubMessage(
                    format=AllowedFormats(message.format),  # <- coerce str -> enum
                    subformat=message.subformat,
                    content=message.content,
                    label=message.label,
                )
            ]

        run_msgs: list[NLIP_Message] = [
            NLIP_Message(
                messagetype=message.messagetype or "request",
                format=s.format,
                subformat=s.subformat,
                content=s.content,
                label=s.label,
            )
            for s in incoming_subs
        ]

        results: list[NLIP_Message] = await asyncio.gather(
            *[asyncio.create_task(self.dispatch(rm)) for rm in run_msgs]
        )

        out_subs: list[NLIP_SubMessage] = [
            NLIP_SubMessage(
                format=AllowedFormats(r.format),
                subformat=r.subformat,
                content=r.content,
                label=r.label,
            )
            for r in results
        ]

        overall = "ok" if all((getattr(r, "messagetype", "") or "").lower() != "error" for r in results) else "partial"
        
        return NLIP_Message(
            messagetype="response",
            format=AllowedFormats.generic,
            subformat="nlip.bundle",
            content=overall,
            label=getattr(message, "label", None) or "bundle_result",
            submessages=out_subs,
        )