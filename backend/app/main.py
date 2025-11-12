import asyncio
import sys

from .servers.basic_server import app as basic
from .servers.coordinator_server import app as coord
from .servers.translate_server import app as translate
from .system.mount_spec import MountSpec

if __name__ == "__main__":
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