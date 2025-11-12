import asyncio
import logging
from fastapi import FastAPI, Body, Request, Response, Depends, HTTPException
from typing import Dict, Annotated
from uuid import uuid4
import traceback
import sys
from contextlib import asynccontextmanager
from nlip_sdk.nlip import NLIP_Message

logger = logging.getLogger("NLIP")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Lifespan started")
    try:
        yield
    except asyncio.CancelledError:
        logger.debug("Lifespan cancelled")
    finally:
        pass

class SessionManager:
    async def process_nlip(self, msg: NLIP_Message) -> NLIP_Message:
        raise NotImplementedError("process_nlip must be implemented by subclasses")
    
class NlipSessionServer(FastAPI):
    def __init__(self, suffix: str, session_manager_class):
        super().__init__(lifespan=lifespan)
        self.suffix = suffix
        self.session_manager_class = session_manager_class
        self.session_cookie_name = f"session_id_{suffix}"
        self.sessions: Dict[str, SessionManager] = {}

        app = self

        @app.post("/nlip")
        async def process_nlip_request(
            message: Annotated[NLIP_Message, Body(examples=examples)],
            manager: SessionManager = Depends(self.get_session_manager)
        ):
            try:
                response = await manager.process_nlip(message)
                return response
            except Exception as e:
                logger.error(f"Error processing NLIP message: {str(e)}")
                traceback.print_exc(file=sys.stderr)
                raise HTTPException(status_code=400, detail=str(e))
            
        @app.get("/health")
        async def health_check():
            return {"status": "ok"}
            
    def get_session_manager(self, request: Request, response: Response) -> SessionManager:
        session_id = request.cookies.get(self.session_cookie_name)
        
        if not session_id or session_id not in self.sessions:
            session_id = str(uuid4())
            self.sessions[session_id] = self.session_manager_class()

            response.set_cookie(
                key=self.session_cookie_name,
                value=session_id,
                httponly=True,
                samesite="lax",
            )
            logger.debug(f"Created new session with ID: {session_id}")
        return self.sessions[session_id]




examples = [
    {
        "format": "text",
        "subformat":"english",
        "content": "How are you today?"
    },
    {
        "format": "text",
        "subformat":"english",
        "content": "Is there a weather alert for CA?"
    },
    {
        "format": "text",
        "subformat":"english",
        "content": "Describe your NLIP Capabilities."
    },
]