from __future__ import annotations

"""
Coordinator NLIP server entrypoint.

Replaces the previous /nlip route with a sessioned Coordinator that discovers
agents via addresses-only MOUNT_SPEC and communicates using connect/send tools.
"""

from fastapi import FastAPI

from app.agents.coordinator_nlip_agent import CoordinatorNlipAgent
from app.http_server.nlip_session_server import NlipSessionServer, SessionManager
from app.system.mount_spec import MOUNT_SPEC, register_mem_apps


# Ensure in-proc mem:// apps are available for transport
register_mem_apps(MOUNT_SPEC)


class CoordinatorManager(SessionManager):
    def __init__(self) -> None:
        self.agent = CoordinatorNlipAgent("Coordinator")

    async def process_nlip(self, msg):
        return await self.agent.handle(msg)


# Expose the sessioned Coordinator at /nlip
app: FastAPI = NlipSessionServer("CoordinatorCookie", CoordinatorManager)
