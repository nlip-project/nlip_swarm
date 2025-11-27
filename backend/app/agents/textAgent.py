"""Text agent with tools backed by the hosted Cerebras model."""

from __future__ import annotations

import logging
import os
from typing import Optional, Any, cast

from litellm import acompletion

from .nlip_agent import NlipAgent
from .base import MODEL

logger = logging.getLogger("NLIP")


TEXT_TOOL_MODEL = os.getenv("TEXT_TOOL_MODEL", MODEL)
TEXT_TOOL_SYSTEM = (
    "You are an NLIP text assistant. Provide concise yet complete answers, cite facts when "
    "possible, and clearly note if critical information is missing."
)


async def generate_text(prompt: str, context: Optional[str] = None) -> str:
    """Generate a response with the hosted Cerebras model instead of local Ollama."""

    segments = [prompt.strip()]
    if context:
        segments.insert(0, context.strip())

    messages = [
        {"role": "system", "content": TEXT_TOOL_SYSTEM},
        {"role": "user", "content": "\n\n".join(filter(None, segments)) or "Provide a short update."},
    ]

    try:
        response = await acompletion(model=TEXT_TOOL_MODEL, messages=messages)
    except Exception as exc:  # pragma: no cover - upstream outages
        logger.exception("Cerebras text tool request failed: %s", exc)
        return "Unable to generate text because the Cerebras request failed."

    response_message = cast(Any, response).choices[0].message
    content = getattr(response_message, "content", None)
    if not content:
        content = response_message.get("content") if isinstance(response_message, dict) else None

    if isinstance(content, list):
        text_parts = []
        for fragment in content:
            if isinstance(fragment, dict) and isinstance(fragment.get("text"), str):
                text_parts.append(fragment["text"])
            elif isinstance(fragment, str):
                text_parts.append(fragment)
        content = " ".join(text_parts)

    if not isinstance(content, str):
        return "The Cerebras model returned an unexpected payload."

    return content.strip()


class TextNlipAgent(NlipAgent):
    """Agent that reasons about prompts and can call `generate_text`."""

    def __init__(
        self,
        name: str = "Text",
        model: str = MODEL,
        instruction: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, model=model, instruction=instruction, tools=[generate_text])

        self.add_instruction(
            "You can draft, edit, and reason about natural language using the `generate_text` tool, "
            "which calls a hosted Cerebras model for higher quality results."
        )
