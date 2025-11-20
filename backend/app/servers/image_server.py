from __future__ import annotations

"""NLIP server wrapper for the ImageNlipAgent."""

from nlip_sdk.nlip import NLIP_Factory, NLIP_Message

from app.agents.imageRecognition import ImageNlipAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager
from app.agents.imageRecognition import describe_image


CAP_QUERY_PHRASES = {
    "describe your nlip capabilities.",
    "what are your nlip capabilities?",
}


def _capabilities_text(agent: ImageNlipAgent) -> str:
    capabilities = [
        "IMAGE_DESCRIPTION:Describes images using the describe_image tool backed by a Llava-compatible endpoint.",
        "PROMPT_GUIDANCE:Accepts optional prompts to steer the description.",
        "DATA_URL_STRIPPING:Handles base64 payloads or data URLs for images.",
    ]
    return f"AGENT:{agent.name}\n" + ", ".join(capabilities)


def _clean_outputs(outputs: list[str]) -> list[str]:
    cleaned = [entry for entry in outputs if entry and not entry.startswith("Calling tool:")]
    return cleaned or [""]


class ImageSessionManager(SessionManager):
    def __init__(self) -> None:
        self.agent = ImageNlipAgent("image")

    def process_image(self, text: str, image_payload: str) -> str:
        prompt = text or "The user did not supply extra instructions."
        request = ("You have received an NLIP request that includes an image.\n"
            "Call the `describe_image` tool exactly once, using the prompt below "
            "and the base64 payload exactly as provided between IMAGE_BASE64_BEGIN/END.\n"
            "PROMPT:\n"
            f"{prompt}\n"
            "IMAGE_BASE64_BEGIN\n"
            f"{image_payload}\n"
            "IMAGE_BASE64_END\n"
            "Do not fabricate or shorten the base64 string; copy it verbatim into the `image_base64` argument."
        )
        return request

    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        text = msg.extract_text()
        # fmt = msg.extract_field_list(format="binary", subformat="image/base64")
        # if fmt:
        #     # request = self.process_image(text, fmt[0])
        #     respones = await describe_image(image_base64=fmt[0], prompt=text)
        #     return NLIP_Factory.create_text(respones)
        # else:
        #     # print("No image format found in NLIP message submessages.")
        #     request = text
        if not text:
            return NLIP_Factory.create_text("Image agent expects textual content.")

        normalized = text.strip().lower()
        if normalized in CAP_QUERY_PHRASES:
            return NLIP_Factory.create_text(_capabilities_text(self.agent))

        try:
            raw_results = await self.agent.process_query(text)
        except Exception as exc:  # pragma: no cover - defensive logging
            return NLIP_Factory.create_text(f"Error processing image request: {exc}")

        results = _clean_outputs(raw_results)
        response = NLIP_Factory.create_text(results[0])
        for extra in results[1:]:
            response.add_text(extra)
        return response


app = NlipSessionServer("ImageAgentCookie", ImageSessionManager)
