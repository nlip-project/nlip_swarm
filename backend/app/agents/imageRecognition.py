"""Image helper that calls a local Docker Model Runner vision model."""

from __future__ import annotations

import base64
import os
from typing import Optional

import httpx

from app._logging import logger


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL") or os.getenv("OLLAMA_MODEL", "ai/ministral3")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))


def _strip_data_url(image_base64: str) -> str:
    if "," in image_base64 and image_base64.strip().startswith("data:"):
        return image_base64.split(",", 1)[1]
    return image_base64


def _chat_completions_url(base: str) -> str:
    normalized = base.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _coerce_message_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


async def describe_image(image_base64: str, prompt: Optional[str] = None) -> str:
    """Describe an image by calling the configured vision model over OpenAI API.

    Args:
        image_base64: Base64 encoded image data or data URL.
        prompt: Optional guiding instruction for the caption.
    """
    clean_b64 = _strip_data_url(image_base64)
    try:
        base64.b64decode(clean_b64, validate=True)
    except Exception:  # pragma: no cover - invalid user input
        return "The provided image payload is not valid base64 data."

    image_data_url = f"data:image/jpeg;base64,{clean_b64}"
    payload = {
        "model": OLLAMA_IMAGE_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe everything that can be observed in this image."},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        "stream": False,
    }

    url = _chat_completions_url(OLLAMA_URL)
    logger.debug("Image agent calling vision model", extra={"url": url, "model": OLLAMA_IMAGE_MODEL})

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc: 
            logger.exception("Vision request failed: %s", exc)
            return "Unable to analyze the image because the local vision model request failed."

    try:
        data = response.json()
    except ValueError:
        logger.exception("Vision response was not valid JSON")
        return "Unable to analyze the image because the model response was invalid."

    try:
        choice = data["choices"][0]["message"]["content"]
    except Exception:
        return "The vision endpoint returned an unexpected payload."

    content = _coerce_message_content(choice)
    if not content:
        return "The vision endpoint returned an empty response."
    return content
