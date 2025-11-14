"""FastAPI wrapper exposing a Whisper-compatible transcription endpoint."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Optional

import whisper
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse


app = FastAPI(title="Local Whisper Server")

# Cache models so subsequent requests reuse the loaded weights
_MODEL_CACHE: dict[tuple[str, Optional[str]], whisper.Whisper] = {}


def _get_model(name: str, device: Optional[str]) -> whisper.Whisper:
    key = (name, device)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = whisper.load_model(name, device=device)
    return _MODEL_CACHE[key]


@app.post("/v1/audio/transcriptions")
async def transcribe(
    audio: UploadFile = File(...),
    model: str = Form("large-v3"),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
):
    """Handle Whisper-style transcription requests."""

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        whisper_model = _get_model(model, getattr(app.state, "device", None))
        result = whisper_model.transcribe(str(tmp_path), task=task, language=language)
    except Exception as exc:  # pragma: no cover - runtime errors bubble to client
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    response = {
        "text": result.get("text", ""),
        "language": result.get("language", language),
        "segments": result.get("segments", []),
    }
    return JSONResponse(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Whisper transcription server")
    parser.add_argument("--model", default="large-v3", help="Whisper model to load")
    parser.add_argument("--port", default=9002, type=int, help="HTTP port")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--device", default=None, help="Torch device override (e.g. cuda)")
    args = parser.parse_args()

    app.state.device = args.device

    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
