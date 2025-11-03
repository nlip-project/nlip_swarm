import os
from typing import Optional
import base64

import httpx


class LlavaImageRecognitionAgent:
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = (model or os.getenv("OLLAMA_IMAGE_MODEL", "llava"))

    def recognize_image(self, encodedImage: str, prompt: Optional[str] = None) -> str:
        # Placeholder for image recognition logic
        # In a real implementation, this would involve loading the image
        # and passing it through the Llama model for recognition.

        #encodedImage = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")
        # Base64 encoded string sent over via NLIP message, so just process that directly

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt or "Describe the content of this image in detail.",
            "images": [encodedImage],
            "stream": False, # No streaming for simplicity right now, dont' have to deal with async generator
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

# imageDescription = LlavaImageRecognitionAgent().recognize_image("./test.jpg")
# print("Image Description:", imageDescription.get("response"))
    def test_image_recognition(self, image_path: str, prompt: str):
        encodedImage = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")
        imageDescription = LlavaImageRecognitionAgent().recognize_image(encodedImage, prompt)
        print("Image Description:", imageDescription.get("response")) 

# LlavaImageRecognitionAgent().test_image_recognition("./test.jpg", "State the country of this image and nothing else.")
