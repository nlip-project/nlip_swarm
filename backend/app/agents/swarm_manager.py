from __future__ import annotations
import asyncio
from .base import Agent
from collections import defaultdict, deque
from nlip_sdk.nlip import NLIP_Message, NLIP_Factory, AllowedFormats, NLIP_SubMessage
from ..deprecated.registry import AgentRegistry
from ..deprecated.router import route
from .translation import TranslationError, OllamaTranslationAgent
from typing import List, Deque, List, Tuple, Dict

class SwarmManager(Agent):
    """
    Swarm Manager Agent Class

    __init__(registry: AgentRegistry, router_llm)
    - registry: The AgentRegistry containing all available agents, list of agents
    - router_llm: The model used for routing decisions by the swarm manager

    dispatch(subMessage: NLIP_Message) -> NLIP_Message
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

        self.sessions: Dict[str, Dict[str, object]] = defaultdict(
            lambda: {"lang": "en", "history": deque(maxlen=20)}
        )

    def _get_conv_id(self, message: NLIP_Message) -> str:
        conv = message.extract_conversation_token()
        if not conv:
            conv = message.label or "conv-default"
        return conv
    
    def _push_history(self, conv_id: str, role: str, text: str):
        if not text:
            return
        hist: Deque[Tuple[str, str]] = self.sessions[conv_id]["history"]  # type: ignore[assignment]
        hist.append((role, text))

    def _get_history_text(self, conv_id: str) -> str:
        hist: Deque[Tuple[str, str]] = self.sessions[conv_id]["history"]  # type: ignore[assignment]
        return "\n".join([f"{role.upper()}: {text}" for role, text in list(hist)[-8:]])
    
    def _remember_lang(self, conv_id: str, incoming_text: str):
        try:
            code = self.translator.detect_language(incoming_text or "") or "en"
            self.sessions[conv_id]["lang"] = code
        except TranslationError:
            pass
        #Defaults to 'en'
    
    def _target_lang(self, conv_id: str) -> str:
        return str(self.sessions[conv_id]["lang"])

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

    async def dispatch(self, conv_id: str, subMessage: NLIP_Message, src_lang: str) -> NLIP_Message:
        history_text = self._get_history_text(conv_id)
        agent = await route(
            self.registry,
            subMessage,
            self.router_llm,
            build_prompt=None,  # use default builder
            history_text=history_text,
        )
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
        conv_id = self._get_conv_id(message)

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
            self._remember_lang(conv_id, text_for_lang)
            if isinstance(s.content, str):
                self._push_history(conv_id, "user", s.content)
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
            *[
                asyncio.create_task(self.dispatch(conv_id, rm, src_lang)) 
                for rm, src_lang in zip(run_msgs, input_langs)
                ]
        )

        localized_results: List[NLIP_Message] = [
            self._maybe_localize_text(src_lang, r)
            for src_lang, r in zip(input_langs, results)
        ]

        for r in localized_results:
            if r.format == AllowedFormats.text and isinstance(r.content, str):
                self._push_history(conv_id, "assistant", r.content)

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
