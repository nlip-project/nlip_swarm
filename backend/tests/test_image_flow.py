# backend/tests/test_image_flow.py
import os
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.deprecated.supervisor import process_nlip  # for monkeypatching
from nlip_sdk import nlip
def mock_recognize_image(self, encodedImage: str, prompt: str) -> str:
    payload = nlip.NLIP_Factory.create_binary(
        content=encodedImage,
        binary_type="image",
        encoding="base64",
    )
    payload.add_submessage(
        nlip.NLIP_Factory.create_text(
            content=prompt,
            language="en",
            label="prompt"
        )
    )

    return process_nlip(payload)

# Specify image path and prompt
# image_path = "./backend/tests/test.jpg"
# prompt = "Describe the vegetation in this image."
# fake_b64 = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")

# print(process_nlip(payload))