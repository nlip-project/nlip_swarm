#!/usr/bin/env python
"""
Minimal FastAPI server that exposes an OpenAI-compatible
`POST /v1/audio/transcriptions` endpoint using the openai-whisper package.

It is intended for local development only and mirrors the behavior expected by
`backend.app.agents.sound.SoundAgent`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
from functools import partial
from typing import Any, Dict, Optional

import uvicorn
import whisper
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_MODEL = "large-v3"

MODEL_ALIASES = {
    "whisper-tiny": "tiny",
    "whisper-base": "base",
    "whisper-small": "small",
    "whisper-medium": "medium",
    "whisper-large": "large",
    "whisper-large-v2": "large-v2",
    "whisper-large-v3": "large-v3",
}


class WhisperModelCache:
    """Lazily loads and caches Whisper models so repeated requests reuse weights."""

    def __init__(self, device: Optional[str] = None) -> None:
        self._device = device
        self._models: Dict[str, Any] = {}

    def get(self, name: str) -> Any:
        canonical = self._normalize(name)
        if canonical not in self._models:
            self._models[canonical] = whisper.load_model(canonical, device=self._device)
        return self._models[canonical]

    @staticmethod
    def _normalize(name: str) -> str:
        key = (name or DEFAULT_MODEL).strip().lower()
        return MODEL_ALIASES.get(key, key)


def build_app(model_cache: WhisperModelCache) -> FastAPI:
    app = FastAPI(title="Local Whisper Server", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/v1/audio/transcriptions")
    async def transcribe_audio(
        model: str = Form(DEFAULT_MODEL),
        language: Optional[str] = Form(None),
        temperature: float = Form(0.0),
        audio: UploadFile = File(...),
    ) -> Dict[str, object]:
        payload = await audio.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        tmp_suffix = os.path.splitext(audio.filename or ".wav")[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=tmp_suffix, delete=False) as tmp:
            tmp.write(payload)
            tmp_path = tmp.name

        loop = asyncio.get_event_loop()
        try:
            model_instance = model_cache.get(model)
            transcribe = partial(
                model_instance.transcribe,
                tmp_path,
                language=language,
                temperature=temperature,
            )
            result = await loop.run_in_executor(None, transcribe)
        except Exception as exc:  # pragma: no cover - surfaced to HTTP clients
            raise HTTPException(status_code=500, detail=f"Whisper failed: {exc}") from exc
        finally:
            os.unlink(tmp_path)

        return {
            "model": model,
            "text": result.get("text", ""),
            "language": result.get("language"),
            "segments": [
                {
                    "id": segment.get("id"),
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "text": segment.get("text"),
                }
                for segment in result.get("segments", [])
            ],
        }

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local Whisper HTTP server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9002, help="Port to expose (default: 9002)")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Default Whisper model to preload (default: large-v3)",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Optional torch device override (e.g. cpu, cuda). Defaults to auto.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache = WhisperModelCache(device=args.device)
    # Preload the default model so the first request is not penalized.
    cache.get(args.model)
    app = build_app(cache)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
