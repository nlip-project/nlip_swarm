from __future__ import annotations

"""
In‑process NLIP app registry for mem:// transport.

Agents wrapped as FastAPI NLIP servers can be mounted at a logical
mem://<name> address by registering their ASGI app here. The async
NLIP client will route mem:// requests to these apps via httpx.ASGITransport.
"""

from typing import Dict
from fastapi import FastAPI

#In-memory agent registry
MEM_APP_TBL: Dict[str, FastAPI] = {}

def asgi_register(name: str, app: FastAPI) -> None:
    """Register a FastAPI app under a mem address name."""
    MEM_APP_TBL[name] = app

