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


def _ollama_generate_url(base: str) -> str:
    normalized = base.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return f"{normalized.rstrip('/')}/api/generate"


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


def _error_snippet(response: httpx.Response) -> str:
    try:
        text = response.text
    except Exception:
        return ""
    text = (text or "").strip()
    return text[:500]


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
    openai_payload = {
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
    ollama_payload = {
        "model": OLLAMA_IMAGE_MODEL,
        "prompt": prompt or "Describe everything that can be observed in this image.",
        "images": [clean_b64],
        "stream": False,
    }

    openai_url = _chat_completions_url(OLLAMA_URL)
    ollama_url = _ollama_generate_url(OLLAMA_URL)
    logger.debug(
        "Image agent calling vision model",
        extra={"openai_url": openai_url, "ollama_url": ollama_url, "model": OLLAMA_IMAGE_MODEL},
    )

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        response: Optional[httpx.Response] = None
        try:
            response = await client.post(openai_url, json=openai_payload)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                logger.exception("Vision response was not valid JSON")
                raise RuntimeError("invalid_openai_json")

            try:
                choice = data["choices"][0]["message"]["content"]
            except Exception:
                raise RuntimeError("unexpected_openai_payload")

            content = _coerce_message_content(choice)
            if content:
                return content
            raise RuntimeError("empty_openai_content")
        except Exception as first_error:
            error_body = _error_snippet(response) if response is not None else ""
            logger.warning(
                "OpenAI vision path failed, trying Ollama fallback",
                extra={
                    "error": str(first_error),
                    "status_code": response.status_code if response is not None else None,
                    "body": error_body,
                    "model": OLLAMA_IMAGE_MODEL,
                },
            )

        fallback_response: Optional[httpx.Response] = None
        try:
            fallback_response = await client.post(ollama_url, json=ollama_payload)
            fallback_response.raise_for_status()
            fallback_data = fallback_response.json()
            fallback_content = fallback_data.get("response") if isinstance(fallback_data, dict) else None
            if isinstance(fallback_content, str) and fallback_content.strip():
                return fallback_content.strip()
            return "The vision endpoint returned an unexpected payload."
        except Exception as fallback_error:
            fallback_body = _error_snippet(fallback_response) if fallback_response is not None else ""
            logger.exception(
                "Ollama fallback failed",
                extra={
                    "error": str(fallback_error),
                    "status_code": fallback_response.status_code if fallback_response is not None else None,
                    "body": fallback_body,
                    "model": OLLAMA_IMAGE_MODEL,
                },
            )
            return "Unable to analyze the image because the local vision model returned an internal error."
