MOUNT_URLS = {
    "coord": "http://0.0.0.0:8024/",
    "basic": "mem://basic/",
    "translate": "mem://translate/",
    "text": "mem://text/",
    "sound": "mem://sound/",
    "image": "mem://image/",
}

COORDINATOR_URL = MOUNT_URLS["coord"]

# All non-coordinator endpoints derived from MOUNT_URLS
DEFAULT_AGENT_ENDPOINTS = [
    url.rstrip("/")
    for name, url in MOUNT_URLS.items()
    if name != "coord"
]
