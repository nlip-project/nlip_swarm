"""NLIP server wrapper for image recognition. Routes requests directly to the describe_image() tool function."""

from __future__ import annotations

from typing import Any, Optional

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from app.agents.imageRecognition import describe_image
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager


CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}


def _capabilities_text() -> str:
    capabilities = [
        "IMAGE_DESCRIPTION:Describes images using local DMR vision model|FORMATS:[binary]|SUBFORMATS:[image]",
        "PROMPT_GUIDANCE:Accepts optional prompts|FORMATS:[text]",
        "DATA_URL_STRIPPING:Handles base64 or data URLs",
    ]
    return "AGENT:image\n" + ", ".join(capabilities)


def _get(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)


def _find_image_content(entry: Any) -> Optional[str]:
    fmt = (_get(entry, "format") or "").lower()
    subfmt = (_get(entry, "subformat") or "").lower()
    content = _get(entry, "content")

    if isinstance(content, str) and content:
        looks_like_image = content.startswith(("data:image", "/9j/", "iVBORw0KG"))
        tagged_as_image = "image" in subfmt or fmt.startswith("binary")
        if looks_like_image or tagged_as_image:
            return content

    for key in ("submessages", "messages"):
        children = _get(entry, key)
        if isinstance(children, list):
            for child in children:
                found = _find_image_content(child)
                if found:
                    return found
    return None


class ImageSessionManager(SessionManager):
    def __init__(self) -> None:
        pass

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()

        if text:
            normalized = text.strip().lower()
            if normalized in CAP_QUERY_PHRASES:
                return NLIP_Factory.create_text(_capabilities_text())

        try:
            msg_dict = msg.to_dict() if hasattr(msg, "to_dict") else msg.model_dump()
        except Exception:
            msg_dict = msg

        image_content = _find_image_content(msg_dict)
        if not image_content:
            return NLIP_Factory.create_text("Image agent expects an NLIP message containing image data.")

        prompt = text.strip() if text and text.strip() else None
        result = await describe_image(image_base64=image_content, prompt=prompt)
        return NLIP_Factory.create_text(result)


app = NlipSessionServer("ImageAgentCookie", ImageSessionManager)
