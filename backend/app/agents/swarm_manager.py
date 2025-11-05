from __future__ import annotations
import asyncio
from typing import List, cast
from .base import Agent
from ..registry import AgentRegistry
from ..router import route
from .translation import TranslationError, OllamaTranslationAgent
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
    def __init__(self, registry: AgentRegistry, router_llm, translator: OllamaTranslationAgent):
        super().__init__(name="swarm_manager", capabilities=["swarm.manage", "plan.dispatch"], llm=router_llm)
        self.registry = registry
        self.router_llm = router_llm
        self.translator = translator

    async def dispatch(self, subMessage: NLIP_Message) -> NLIP_Message:
        agent = await route(self.registry, subMessage, self.router_llm)
        try:
            return await agent.handle(subMessage)
        except Exception as e:
            err = NLIP_Factory.create_text(f"Agent {agent.name} failed: {repr(e)}", label=getattr(subMessage, "label", ''))
            err.messagetype = "error"
            return err
        
    def _detect_lang(self, text: str) -> str:
        try:
            code = self.translator.detect_language(text)
            return code
        except TranslationError:
            return "en"
        
    def _maybe_localize_text(self, src_lang: str, out_message: NLIP_Message) -> NLIP_Message:
        if (out_message.format == AllowedFormats.text and isinstance(out_message.content, str)):
            try:
                if src_lang and src_lang != "en":
                    localized = self.translator.translate(out_message.content, target_locale=src_lang)
                    loc = NLIP_Factory.create_text(localized, label=getattr(out_message, "label", ''))
                    loc.messagetype = out_message.messagetype or "response"
                    loc.subformat = out_message.subformat or "text"
                    return loc
            except TranslationError:
                pass
        return out_message

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

        run_msgs: list[NLIP_Message] = []
        input_langs: list[str] = []
        for s in incoming_subs:
            text_for_lang = s.content if isinstance(s.content, str) else ""
            src_lang = self._detect_lang(text_for_lang) if text_for_lang else "en"
            input_langs.append(src_lang)
            run_msgs.append(
                NLIP_Message(
                    messagetype="request",
                    format=s.format,
                    subformat=s.subformat,
                    content=s.content,
                    label=s.label,
                )
            )

        results: list[NLIP_Message] = await asyncio.gather(
            *[asyncio.create_task(self.dispatch(rm)) for rm in run_msgs]
        )

        localized_results: List[NLIP_Message] = [
            self._maybe_localize_text(src_lang, r)
            for src_land, r in zip(input_langs, results)
        ]

        out_subs: list[NLIP_SubMessage] = [
            NLIP_SubMessage(
                format=AllowedFormats(r.format),
                subformat=r.subformat,
                content=r.content,
                label=r.label,
            )
            for r in localized_results
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