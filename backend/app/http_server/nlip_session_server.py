import asyncio
import logging
from fastapi import FastAPI, Body, Request, Response, Depends, HTTPException
from typing import Dict, Annotated
from uuid import uuid4
import traceback
import sys
from contextlib import asynccontextmanager
from nlip_sdk.nlip import NLIP_Message
from sqlalchemy.exc import IntegrityError

# DB imports
from app.db import AsyncSessionLocal, init_db
from app.auth import crud, schemas

logger = logging.getLogger("NLIP")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Lifespan started")
    # Ensure database tables exist on startup (no-op if already created)
    try:
        # init_db includes retry/backoff and will raise on final failure
        await init_db()
    except Exception:
        logger.exception("Failed to initialize DB during startup (init_db failed).")
        raise

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
        
        @app.post("/signup")
        async def signup(user: schemas.UserCreate, request: Request, response: Response):
            try:
                logger.info("Signup request: %s", getattr(user, "email", "<no-email>"))
                # existing signup logic (was disabled) - keep small safe behavior while debugging
                # replace this with the real create-user code once we see the root cause
                # async with AsyncSessionLocal() as db:
                #     created = await crud.create_user(db, email=user.email, password=user.password, location=user.location)
                return {"message": "Signup disabled in this build."}
            except Exception as exc:
                logger.exception("Unhandled exception in /signup")
                raise HTTPException(status_code=500, detail="Internal server error")

        class LoginSchema:
            def __init__(self, email: str, password: str):
                self.email = email
                self.password = password

        @app.post("/login")
        async def login(payload: dict, request: Request, response: Response):
            """Login with email & password. Returns a session cookie on success."""
            email = payload.get("email")
            password = payload.get("password")
            if not email or not password:
                raise HTTPException(status_code=400, detail="email and password required")

            async with AsyncSessionLocal() as db:
                user = await crud.get_user_by_email(db, email=email)
                if not user:
                    raise HTTPException(status_code=400, detail="Invalid credentials")
                ok = await crud.verify_password(password, user.password_hash)
                if not ok:
                    raise HTTPException(status_code=400, detail="Invalid credentials")

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
            return {"message": "Logged in", "session_id": session_id, "user_id": user.id}
            
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