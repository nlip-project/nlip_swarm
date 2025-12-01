import asyncio
import logging
from fastapi import FastAPI, Body, Request, Response, Depends, HTTPException
from typing import Dict, Annotated, Optional
from uuid import uuid4
import traceback
import sys
from contextlib import asynccontextmanager
from nlip_sdk.nlip import NLIP_Message
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError

from app.auth.db import init_db, create_user, get_user_by_email, verify_password

logger = logging.getLogger("NLIP")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Lifespan started")
    try:
        await init_db()
        yield
    except asyncio.CancelledError:
        logger.debug("Lifespan cancelled")
    except Exception:
        logger.exception("Failed to initialize DB during startup")
        raise
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
        
        class UserCreate(BaseModel):
            email: EmailStr
            password: str
            location: Optional[str] = None
            
        @app.post("/signup")
        async def signup(user: UserCreate, request: Request, response: Response):
            """
            Expects JSON: {"email": "...", "password": "...", "location": "..."}
            """
            try:
                created = await create_user(email=user.email, password=user.password, location=user.location)
            except IntegrityError:
                raise HTTPException(status_code=400, detail="User with that email already exists")
            # create session as before
            session_id = str(uuid4())
            manager = self.session_manager_class()
            setattr(manager, "user_id", created.id)
            self.sessions[session_id] = manager
            response.set_cookie(
                key=self.session_cookie_name,
                value=session_id,
                httponly=True,
                samesite="lax",
            )
            return {"message": "Signed up", "session_id": session_id, "user_id": created.id}

        @app.post("/login")
        async def login(payload: dict, request: Request, response: Response):
            """
            Expects JSON: {"email": "...", "password": "..."}
            """
            from app.auth.models import User
            from app.auth.db import AsyncSessionLocal
            import bcrypt

            email = payload.get("email")
            password = payload.get("password")
            if not email or not password:
                raise HTTPException(status_code=400, detail="Email and password required")
            
            user = await get_user_by_email(email)
            if not user:
                raise HTTPException(status_code=400, detail="Invalid email or password")
            if not await verify_password(password, user.password):
                raise HTTPException(status_code=400, detail="Invalid email or password")
            
            # create session as before
            session_id = str(uuid4())
            manager = self.session_manager_class()
            setattr(manager, "user_id", user.id)
            self.sessions[session_id] = manager
            response.set_cookie(
                key=self.session_cookie_name,
                value=session_id,
                httponly=True,
                samesite="lax",
            )
            return {
                "message": "Logged in",
                "session_id": session_id,
                "user_id": user.id,
                "email": user.email,
                "location": getattr(user, "location", None),
            }
    
        @app.post("/logout")
        async def logout(request: Request, response: Response):
            session_id = request.cookies.get(self.session_cookie_name)
            if session_id and session_id in self.sessions:
                try:
                    del self.sessions[session_id]
                except KeyError:
                    pass
            # instruct browser to remove cookie
            response.delete_cookie(key=self.session_cookie_name, httponly=True, samesite="lax")
            return {"message": "Logged out"}
            
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