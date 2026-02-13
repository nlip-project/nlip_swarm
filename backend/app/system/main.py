import asyncio
from pathlib import Path
import sys
import logging

from numpy import add

from app.servers.basic_server import app as basic
from app.servers.coordinator_server import app as coord
from app.servers.translate_server import app as translate
from app.servers.text_server import app as text
from app.servers.sound_server import app as sound
from app.servers.image_server import app as image
from .mount_spec import MountSpec
from .config import MOUNT_URLS
from app._logging import log_to_console
from app.system.agentAdder import add_agents_from_spec
from app.system.config import PATHS


if __name__ == "__main__":
    log_to_console(logging.DEBUG)

    mount_spec = [
        (coord, "http://0.0.0.0:8024/"),
        (basic, "mem://basic/"),
        (translate, "mem://translate/"),
        (text, "mem://text/"),
        (sound, "mem://sound/"),
        (image, "mem://image/"),
    ]


    
    path = Path(__file__).parent.parent.parent.joinpath(PATHS["json_path"], "agent_spec.json")
    mount_spec.extend(add_agents_from_spec(str(path)))
    # print(f"Mount spec: {mount_spec}")
    ms = MountSpec(mount_spec)

    try:
        asyncio.run(ms.runall())
    except Exception as e:
        print(f"Fatal error running servers: {e}", file=sys.stderr)
        sys.exit(1)