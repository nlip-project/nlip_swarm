from __future__ import annotations

"""
Session-oriented NLIP FastAPI server.

Exposes two routes:
 - POST /nlip  (body is an NLIP_Message JSON)
 - GET  /health

A cookie-backed session is created on first request. Each session is
associated with a SessionManager instance that handles NLIP messages.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Annotated
from uuid import uuid4

from fastapi import FastAPI, Body, Request, Response, Depends, HTTPException

from nlip_sdk.nlip import NLIP_Message
from app import __name__ as app_pkg_name  # for examples provenance


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    except asyncio.CancelledError:
        # Allow graceful shutdown on Ctrl+C
        pass


class SessionManager:
    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        raise NotImplementedError


class NlipSessionServer(FastAPI):
    def __init__(self, cookie_suffix: str, session_manager_cls):
        super().__init__(lifespan=lifespan)

        self.session_cookie_name = f"session_id_{cookie_suffix}"
        self._session_manager_cls = session_manager_cls
        self._sessions: Dict[str, SessionManager] = {}

        app = self

        @app.post("/nlip")
        async def process_nlip_request(
            message: Annotated[NLIP_Message, Body(examples=_examples)],
            manager: SessionManager = Depends(self._get_session_manager),
        ):
            try:
                return await manager.process_nlip(message)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}

    def _get_session_manager(self, request: Request, response: Response) -> SessionManager:
        sid = request.cookies.get(self.session_cookie_name)
        if not sid or sid not in self._sessions:
            sid = str(uuid4())
            self._sessions[sid] = self._session_manager_cls()
            response.set_cookie(
                key=self.session_cookie_name,
                value=sid,
                httponly=True,
                samesite="lax",
            )
        return self._sessions[sid]


_examples = [
    {
        "format": "text",
        "subformat": "english",
        "content": "How are you today?",
    },
    {
        "format": "text",
        "subformat": "english",
        "content": "Describe your NLIP Capabilities.",
    },
]

