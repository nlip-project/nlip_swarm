from __future__ import annotations

"""
Addresses-only mount specification for the swarm.

Users customize the swarm by editing MOUNT_SPEC to include any mix of:
 - mem://<name>      (in-process FastAPI apps registered in MEM_APP_TBL)
 - http://host[:port]/nlip
 - https://host[:port]/nlip

On startup, the Coordinator session will discover agents by connecting
to each address and asking for NLIP Capabilities.
"""

from typing import Iterable

from fastapi import FastAPI

from app.system.mem_registry import asgi_register


# Default set: in-proc translation + text agents
MOUNT_SPEC: list[str] = [
    "mem://translate",
    "mem://text",
]


def _maybe_import_mem_app(name: str) -> FastAPI | None:
    """Import a known in-proc agent server app by mem name, if available."""
    try:
        if name == "translate":
            from app.servers.translate_server import app as translate_app
            return translate_app
        if name == "text":
            from app.servers.text_server import app as text_app
            return text_app
    except Exception:
        return None
    return None


def register_mem_apps(addresses: Iterable[str]) -> None:
    """Ensure mem:// apps referenced in addresses are present in MEM_APP_TBL.

    This helper imports known server wrappers and registers their ASGI apps
    under the mem name so mem:// transport can reach them in-process.
    """
    for addr in addresses:
        if addr.startswith("mem://"):
            name = addr.split("://", 1)[1]
            app = _maybe_import_mem_app(name)
            if app is not None:
                asgi_register(name, app)

