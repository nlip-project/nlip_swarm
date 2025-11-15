import asyncio
import sys
import logging

from app.servers.basic_server import app as basic
from app.servers.coordinator_server import app as coord
from app.servers.translate_server import app as translate
from app.servers.image_server import app as image
from .mount_spec import MountSpec
from .config import MOUNT_URLS
from app._logging import log_to_console


if __name__ == "__main__":
    log_to_console(logging.DEBUG)

    mount_spec = [
        (coord, MOUNT_URLS["coord"]),
        (basic, MOUNT_URLS["basic"]),
        (translate, MOUNT_URLS["translate"]),
        (image, MOUNT_URLS["image"]),
    ]

    ms = MountSpec(mount_spec)

    try:
        asyncio.run(ms.runall())
    except Exception as e:
        print(f"Fatal error running servers: {e}", file=sys.stderr)
        sys.exit(1)
