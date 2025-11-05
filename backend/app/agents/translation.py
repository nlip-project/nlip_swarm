import os
import logging
from typing import Optional
from .base import Agent
from nlip_sdk.nlip import NLIP_Message, NLIP_Factory

import httpx

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when the Ollama translation agent cannot complete a request."""


def _infer_locale(subformat: Optional[str]) -> Optional[str]:
    if not subformat:
        return None
    parts = subformat.split(".")
    if len(parts) >= 3 and parts[0] == "task" and parts[1] == "translate":
        return parts[2]
    if len(parts) >= 2 and parts[0] == "translate":
        return parts[1]
    return None

class OllamaTranslationAgent(Agent):
    """
    Simple translation agent that delegates translation requests to a locally
    running Ollama instance.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(
            name="ollama_translation",
            capabilities=["task.translate.*", "task.translate"],
            llm=None,
        )
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or "llama3.1"
        self.timeout = timeout

    async def handle(self, message: NLIP_Message) -> NLIP_Message:
        text = message.content if isinstance(message.content, str) else ("" if message.content is None else str(message.content))
        target = _infer_locale(getattr(message, "subformat", None)) or "en"

        try:
            translated = self.translate(text, target_locale=target)
            return NLIP_Factory.create_text(translated, label=getattr(message, "label", ''))
        except Exception as e:
            err = NLIP_Factory.create_text(f"translation failed: {e}", label=getattr(message, "label", ''))
            err.messagetype = "error"
            return err

    def translate(self, text: str, target_locale: Optional[str] = None) -> str:
        """
        Translate the provided text into the desired locale using Ollama.

        Parameters
        ----------
        text:
            The source text to translate.
        target_locale:
            Locale to translate into (e.g., 'en', 'es-ES'). Defaults to English.

        Returns
        -------
        str
            The translated text content.
        """
        if not text:
            raise TranslationError("Cannot translate empty text input.")

        locale = target_locale or "en"
        prompt = self._build_prompt(text=text, locale=locale)
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            log.debug(f"[TRANSLATE] model={self.model} text='{text[:80]}' target={target_locale}")
            log.debug(f"[TRANSLATE] POST {url} with stream=False")
            response = httpx.post(url, json=payload, timeout=self.timeout)
            log.error(f"[OLLAMA {url}] HTTP {response.status_code} body={response.text}")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TranslationError(f"Ollama request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Received non-JSON response from Ollama.") from exc

        translated = data.get("response")
        if not translated:
            raise TranslationError("Ollama response did not include translated text.")

        return translated.strip()

    @staticmethod
    def _build_prompt(*, text: str, locale: str) -> str:
        """
        Create the prompt sent to Ollama. The prompt constrains the response so
        the agent returns only the translated text.
        """
        return (
            "You are a translation engine. Translate the user text into the "
            f"locale '{locale}'. Output the translation verbatim and nothing else. "
            "Do not add greetings, apologies, or explanations. If you cannot translate, "
            "respond with exactly '[translation-error]'.\n\n"
            "User text:\n"
            f"{text}\n\n"
            "Translated text:"
        )
