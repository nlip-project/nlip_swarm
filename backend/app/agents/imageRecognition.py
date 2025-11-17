import os
from typing import Optional, Any, Dict
import base64
import asyncio
import logging

import httpx
from .nlip_agent import NlipAgent

logger = logging.getLogger("NLIP")

MODEL = "cerebras/llama3.3-70b"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL", "llava")


# TOOL DEFINITION
async def recognize_image(encodedImage: str, prompt: Optional[str] = None) -> Optional[str]:
    """
    Recognize and describe a base64-encoded image using the configured Ollama
    image model (e.g. llava) by posting the base64 image to the /api/generate
    endpoint.

    - `encodedImage`: base64 string of the image bytes (no data URI prefix).
    - `prompt`: optional instruction for what to describe; falls back to a default prompt.

    Returns a natural-language description string, or None on error.
    """
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_IMAGE_MODEL,
        "prompt": prompt or "Describe the content of this image in detail.",
        "images": [encodedImage],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"Error while requesting {getattr(exc.request, 'url', url)!r}: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        logger.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc}")
        return None

    try:
        data: Dict[str, Any] = response.json()
    except ValueError:
        logger.error("Failed to parse JSON response from image model")
        return None

    description = data.get("response")
    if isinstance(description, str):
        return description

    return None

class ImageRecognitionNlipAgent(NlipAgent):
    """NLIP Image Recognition Agent with recognition tools."""
    def __init__(
            self,
            name: str = "Image",
            model: str = MODEL,
            instruction: Optional[str] = None,
            tools = [recognize_image],
    ) -> None:
        super().__init__(name=name, model=model, tools=tools)

        self.add_instruction("You are an agent with tools for recognizing and describing images.")

        if instruction:
            self.add_instruction(instruction)
