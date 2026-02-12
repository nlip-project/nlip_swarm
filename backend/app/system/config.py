import os


def _env_url(key: str, default: str) -> str:
    raw = os.getenv(key, default)
    return raw.rstrip("/")


MOUNT_URLS = {
    "coord": _env_url("NLIP_COORD_URL", "http://0.0.0.0:8024"),
    "basic": _env_url("NLIP_BASIC_URL", "mem://basic"),
    "translate": _env_url("NLIP_TRANSLATE_URL", "mem://translate"),
    "text": _env_url("NLIP_TEXT_URL", "mem://text"),
    "sound": _env_url("NLIP_SOUND_URL", "mem://sound"),
    "image": _env_url("NLIP_IMAGE_URL", "mem://image"),
}

COORDINATOR_URL = MOUNT_URLS["coord"]

# All non-coordinator endpoints derived from MOUNT_URLS
DEFAULT_AGENT_ENDPOINTS = [url for name, url in MOUNT_URLS.items() if name != "coord"]
