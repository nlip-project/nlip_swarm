import os
import httpx

from nlip_sdk import nlip
from .base import Agent
from typing import Any as NLIP_Message, Optional

class LLamaTextAgent(Agent):
    """
    LLama Text Agent

    An agent that utilizes the LLama model for text-based tasks.

    handle(NLIP_Message) -> NLIP_Message
    - defines how to handle an NLIP message using the LLama model

    """

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = (model or os.getenv("OLLAMA_TEXT_MODEL", "llama3.2:3b"))
    
    

    def handle(self, message: NLIP_Message) -> NLIP_Message:
        text = ""
        if message.format == "text" and message.content is not None:
            text = message.content
        else:
            raise ValueError("Unsupported message format or empty content.")

        # Process the text using the LLama model
        try:
            modelResponse = self.promptResponse(text)
        except Exception as e:
            return nlip.NLIP_Factory.create_text(
                messagetype="error",
                content=f"Error processing request: {str(e)}",
                language="en",
                label="llama_response"
            )
        
        return nlip.NLIP_Factory.create_text(
            content=modelResponse.get("response", ""),
            language="en",
            label="llama_response"
        )
    
    def promptResponse(self, prompt: str) -> NLIP_Message:
        # Generate a response based on the prompt and context
        # context = {}  # Define context as needed
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt or "Describe the content of this image in detail.",
            "stream": False, # No streaming for simplicity right now, don't have to deal with async generator
        }

        try:
            response = httpx.post(url, json=payload, timeout=60)
            response.raise_for_status()

        except httpx.RequestError as exc:
            print(f"Error while requesting {exc.request.url!r}.")
            return ""
        except httpx.HTTPStatusError as exc:
            print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
            return ""
        
        try:
            data = response.json()
            return data
        except ValueError:
            print("Failed to parse JSON response")
            return ""

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