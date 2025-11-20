"""Tests that an NLIP image payload mirrors the Expo client contract."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

if "backend" not in sys.modules:
	ROOT = Path(__file__).resolve().parents[2]
	if str(ROOT) not in sys.path:
		sys.path.insert(0, str(ROOT))

from backend.app.servers import coordinator_server
import nlip_sdk.nlip as nlip


def _load_test_image_b64() -> str:
	"""Return the bundled test.jpg as ASCII base64 for NLIP submessages."""
	image_path = Path(__file__).with_name("test.jpg")
	return base64.b64encode(image_path.read_bytes()).decode("ascii")


def test_image_message_posts_to_nlip():
	encodedImage = _load_test_image_b64()
	client = TestClient(coordinator_server.app)

	prompt = "Describe the climate in this image."
	message = nlip.NLIP_Factory.create_text(content=prompt)
	message.add_submessage(
		nlip.NLIP_Factory.create_binary(
			content=encodedImage,
			binary_type="image",
			encoding="base64",
		)
	)

	response = client.post("/nlip", json=message.model_dump())

	errors: list[str] = ["Unable to describe image",
					  "The provided image payload is not valid base64 data",
					  "Unable to analyze the image because the Llava request failed.",
					  "Unable to analyze the image because the Llava response was invalid.",
					  "The Llava endpoint returned an unexpected payload."]

	assert response.status_code == 200
	body = response.json()
	print(f'Response body: {body}')
	# ensure no error payload was returned
	assert not body.get("content", "").startswith(tuple(errors)) # Make sure no error strings are in the response
