import os


def _env_url(key: str, default: str) -> str:
    raw = os.getenv(key, default)
    return raw.rstrip("/")


MOUNT_URLS = {
    "coord": _env_url("NLIP_COORD_URL", "http://0.0.0.0:8024"),
    # Default to container-to-container HTTP endpoints inside Docker. Override with
    # NLIP_*_URL env vars if you run the agents in-process and want in-memory ASGI
    # routing (mem://...).
    "basic": _env_url("NLIP_BASIC_URL", "http://basic:8025"),
    "translate": _env_url("NLIP_TRANSLATE_URL", "http://translate:8026"),
    "text": _env_url("NLIP_TEXT_URL", "http://text:8027"),
    "sound": _env_url("NLIP_SOUND_URL", "http://sound:8029"),
    "image": _env_url("NLIP_IMAGE_URL", "http://image:8028"),
}

COORDINATOR_URL = MOUNT_URLS["coord"]

# All non-coordinator endpoints derived from MOUNT_URLS
DEFAULT_AGENT_ENDPOINTS = [url for name, url in MOUNT_URLS.items() if name != "coord"]

# Model name registry — used as fallbacks when agent_spec.json omits a model.
MODELS: dict[str, str] = {
    "base_model": os.getenv("OLLAMA_MODEL", "ai/llama3.2:3B-Q4_0"),
    "audio_model": os.getenv("WHISPER_MODEL", "large-v3"),
}

# Path config — json_path locates agent_spec.json relative to the backend root.
PATHS: dict[str, str] = {
    "json_path": os.getenv("AGENT_SPEC_PATH", ""),
}
