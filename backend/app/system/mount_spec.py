import asyncio
import uvicorn
from urllib.parse import urlparse
import logging

from app import MEM_APP_TBL

logger = logging.getLogger("MOUNT_SPEC")

class MountSpec:
    def __init__(self, mount_spec):
        self.mount_spec = mount_spec

    async def create_webserver(self, spec):
        logger.info(f"MountSpec: CREATE_WEBSERVER: {spec}")
        app = spec[0]
        u = urlparse(spec[1])

        logger.debug(f"MountSpec: SCHEME: {u.scheme}")

        if u.scheme == "http":
            if u.port is None:
                raise Exception("Port must be specified for http webserver")

            server_config = uvicorn.Config(app, host="0.0.0.0", port=int(u.port), log_level="info")
            server = uvicorn.Server(server_config)
            logger.debug(f"MountSpec: SERVER:{server}")
            return await server.serve()
        
        elif u.scheme == "mem":
            MEM_APP_TBL[u.hostname] = app
            return None
        else:
            raise Exception(f"Unrecognized webserver scheme: {u.scheme}")
    
    async def runall(self):
        logger.debug("MountSpec: RUNALL")

        servers = []
        for spec in self.mount_spec:
            server = self.create_webserver(spec)
            logger.debug(f"MountSpec: GOT SERVER:{spec} {server}")

            if not spec[1].startswith("mem:"):
                servers.append(asyncio.create_task(server))
            else:
                await server

        try:
            done, pending = await asyncio.wait(servers, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            logger.debug(f"MountSpec: ASYNCIO.WAIT was cancelled")

        for pending_task in pending:
            pending_task.cancel("Another service died, server is shutting down")