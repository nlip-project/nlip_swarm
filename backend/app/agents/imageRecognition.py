import os
from typing import Optional, Any, Dict
import base64

import httpx


class LlavaImageRecognitionAgent:
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = (model or os.getenv("OLLAMA_IMAGE_MODEL", "llava"))

    def recognize_image(self, encodedImage: str, prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt or "Describe the content of this image in detail.",
            "images": [encodedImage],
            "stream": False,
        }

        try:
            response = httpx.post(url, json=payload, timeout=60)
            response.raise_for_status()
        except httpx.RequestError as exc:
            print(f"Error while requesting {exc.request.url!r}.")
            return None
        except httpx.HTTPStatusError as exc:
            print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
            return None

        try:
            data = response.json()
            return data
        except ValueError:
            print("Failed to parse JSON response")
            return None

    def test_image_recognition(self, image_path: str, prompt: str):
        with open(image_path, "rb") as f:
            encodedImage = base64.b64encode(f.read()).decode("utf-8")
        imageDescription = self.recognize_image(encodedImage, prompt)
        if isinstance(imageDescription, dict):
            print("Image Description:", imageDescription.get("response"))
        else:
            print("Image Description: <unavailable>")
