"""Image agent that calls a local Llava model through clearly defined tools."""

from __future__ import annotations

import base64
import os
from typing import Optional

import httpx

from .nlip_agent import NlipAgent

from app._logging import logger


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL") or os.getenv("OLLAMA_MODEL", "ai/llava")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))
LLM_MODEL = f"openai/{os.getenv('OLLAMA_MODEL', OLLAMA_IMAGE_MODEL)}"
LLM_API_BASE = OLLAMA_URL.rstrip("/")


def _strip_data_url(image_base64: str) -> str:
    if "," in image_base64 and image_base64.strip().startswith("data:"):
        return image_base64.split(",", 1)[1]
    return image_base64


async def describe_image(image_base64: str, prompt: Optional[str] = None) -> str:
    """Describe an image by calling the configured Llava model.

    Args:
        image_base64: Base64 encoded image data or data URL.
        prompt: Optional guiding instruction for the caption.
    """
    clean_b64 = _strip_data_url(image_base64)
    try:
        base64.b64decode(clean_b64, validate=True)
    except Exception:  # pragma: no cover - invalid user input
        return "The provided image payload is not valid base64 data."

    payload = {
        "model": OLLAMA_IMAGE_MODEL,
        "prompt": prompt or "Describe everything that can be observed in this image.",
        "images": [clean_b64],
        "stream": False,
    }

    # Docker Model Runner may inject an OpenAI-style endpoint ending in /v1.
    # Ollama image generation API is rooted at /api/generate.
    base_url = OLLAMA_URL[:-3] if OLLAMA_URL.endswith("/v1") else OLLAMA_URL
    url = f"{base_url.rstrip('/')}/api/generate"
    logger.debug("Image agent calling Llava", extra={"url": url, "model": OLLAMA_IMAGE_MODEL})

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc: 
            logger.exception("Llava request failed: %s", exc)
            return "Unable to analyze the image because the Llava request failed."

    try:
        data = response.json()
    except ValueError:
        logger.exception("Llava response was not valid JSON")
        return "Unable to analyze the image because the Llava response was invalid."

    content = data.get("response") if isinstance(data, dict) else None
    if not isinstance(content, str):
        return "The Llava endpoint returned an unexpected payload."
    return content.strip()


class ImageNlipAgent(NlipAgent):
    """NLIP agent exposing the `describe_image` tool."""

    def __init__(
        self,
        name: str = "Image",
        model: str = LLM_MODEL,
        instruction: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            model=model,
            instruction=instruction,
            tools=[describe_image],
            api_base=LLM_API_BASE,
        )

        self.add_instruction(
            "You can help users understand images by calling the `describe_image` tool. "
        )
