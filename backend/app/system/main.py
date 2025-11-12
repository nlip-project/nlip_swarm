import asyncio
import sys
import logging

from app.servers.basic_server import app as basic
from app.servers.coordinator_server import app as coord
from app.servers.translate_server import app as translate
from .mount_spec import MountSpec
from app._logging import log_to_console

if __name__ == "__main__":
    log_to_console(logging.DEBUG)

    mount_spec = [
        (coord, "http://0.0.0.0:8024/"),
        (basic, "mem://basic/"),
        (translate, "mem://translate/"),
    ]

    ms = MountSpec(mount_spec)

    try:
        asyncio.run(ms.runall())
    except Exception as e:
        print(f"Fatal error running servers: {e}", file=sys.stderr)
        sys.exit(1)