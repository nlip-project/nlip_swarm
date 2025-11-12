from __future__ import annotations

"""
Async NLIP client with support for:
 - http:// and https:// via httpx.AsyncClient
 - mem://<name> via httpx.ASGITransport against a FastAPI app stored
   in system.mem_registry.MEM_APP_TBL

The client sends/receives NLIP_Message JSON payloads.
"""

from typing import Optional
from urllib.parse import urlparse

import httpx

from nlip_sdk.nlip import NLIP_Message
from app.system.mem_registry import MEM_APP_TBL


class NlipAsyncClient:
    def __init__(self, base_url: str, timeout: Optional[float] = 120.0):
        self.base_url = base_url
        self.timeout = timeout

        u = urlparse(base_url)

        if u.scheme == "mem":
            app = MEM_APP_TBL.get(u.hostname or "")
            if app is None:
                raise RuntimeError(f"mem:// app '{u.hostname}' not registered")
            transport = httpx.ASGITransport(app=app)
            self.client = httpx.AsyncClient(transport=transport, timeout=timeout)
            self._post_url = (u._replace(scheme="http").geturl()).rstrip("/")
        elif u.scheme in ("http", "https"):
            self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
            self._post_url = base_url.rstrip("/")
        else:
            raise ValueError(f"Unsupported scheme for NLIP client: {u.scheme}")

    @classmethod
    def create_from_url(cls, base_url: str, timeout: Optional[float] = 120.0) -> "NlipAsyncClient":
        return cls(base_url, timeout=timeout)

    async def async_send(self, msg: NLIP_Message) -> NLIP_Message:
        resp = await self.client.post(self._post_url, json=msg.to_dict())
        data = resp.raise_for_status().json()
        return NLIP_Message(**data)

