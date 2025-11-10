import os
from typing import Optional
import httpx

from nlip_sdk.nlip import AllowedFormats, NLIP_Message, NLIP_Factory
from .base import Agent

class LLamaTextAgent(Agent):
    """
    LLama Text Agent

    An agent that utilizes the LLama model for text-based tasks.

    handle(NLIP_Message) -> NLIP_Message
    - defines how to handle an NLIP message using the LLama model

    """
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(
            name="ollama_text",
            capabilities=["task.text", "task.text.*"],
            llm=None,
            )
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = (model or os.getenv("OLLAMA_TEXT_MODEL", "llama3.2:3b"))
   
    

    async def handle(self, message: NLIP_Message) -> NLIP_Message:
        text = ""
        content = message.content if isinstance(message.content, str) else ""
        if content:
            if message.format == AllowedFormats.text:
                text = content
            elif message.format == AllowedFormats.generic and (getattr(message, "subformat", "") or "").startswith("task.text"):
                text = content
        if not text:
            raise ValueError(f"Unsupported message format or empty content. format={message.format}, subformat={getattr(message, 'subformat', None)}")
        try:
            response_text = self.promptResponse(text)
        except Exception as e:
            err = NLIP_Factory.create_text(f"Error processing request: {str(e)}", label="llama_response")
            err.messagetype = "error"
            return err
        return NLIP_Factory.create_text(response_text or "", label="llama_response")
    
    def promptResponse(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt or "Describe the content of this image in detail.",
            "stream": False,
        }
        response = httpx.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        out = data.get("response") if isinstance(data, dict) else None
        if not isinstance(out, str):
            raise ValueError("Invalid response from model")
        return out

# # Example usage:
# print(LLamaTextAgent().promptResponse("What is the capital of France?"))
# nlip.NLIP_Factory.create_text(
#     content="What is the capital of France?",
#     language="en",
#     label="example_prompt"
# )
# print(LLamaTextAgent().handle(nlip.NLIP_Factory.create_text(
#     content="What is the capital of France?",
#     language="en",
#     label="example_prompt"
# )))
