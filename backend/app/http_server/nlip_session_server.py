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
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.auth.db import init_db, create_user, get_user_by_email, verify_password, get_user_by_id, update_user

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
            # Persist conversation and incoming message, then persist assistant response.
            from app.auth.db import AsyncSessionLocal
            from app.models.conversation import Conversation
            from app.models.message import Message
            import uuid as _uuid
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                conv = None
                created_conv = False
                # attempt to read conversation_id from message.metadata or raw dict
                msg_meta = None
                try:
                    # prefer attribute 'metadata' or 'metadata_' if present on NLIP_Message
                    msg_meta = getattr(message, 'metadata', None) or getattr(message, 'metadata_', None)
                except Exception:
                    msg_meta = None

                raw_conv_id = None
                if isinstance(msg_meta, dict):
                    raw_conv_id = msg_meta.get('conversation_id') or msg_meta.get('conversation')

                # If message didn't include a conversation id, try the session's last active conversation
                if not raw_conv_id:
                    last_conv = getattr(manager, 'last_conversation_id', None)
                    if last_conv:
                        raw_conv_id = str(last_conv)

                if raw_conv_id:
                    try:
                        conv_uuid = _uuid.UUID(str(raw_conv_id))
                        result = await session.execute(select(Conversation).where(Conversation.id == conv_uuid))
                        conv = result.scalars().one_or_none()
                    except Exception:
                        conv = None

                # if no conversation was found, create a new one
                if not conv:
                    created_by = getattr(manager, 'user_id', None)
                    conv = Conversation(title=None, created_by=(created_by if created_by is not None else None), metadata_=(msg_meta if isinstance(msg_meta, dict) else None))
                    session.add(conv)
                    await session.commit()
                    await session.refresh(conv)
                    # mark that we created a new conversation during this request
                    created_conv = True
                    # store this conversation as the last active for this session manager
                    try:
                        setattr(manager, 'last_conversation_id', conv.id)
                    except Exception:
                        pass

                # extract a textual representation of the incoming message
                try:
                    incoming_content = getattr(message, 'content', None)
                    if incoming_content is None:
                        # fallback: try str()
                        incoming_content = str(message)
                except Exception:
                    incoming_content = str(message)

                incoming_msg = Message(
                    conversation_id=conv.id,
                    sender_id=getattr(manager, 'user_id', None),
                    role='user',
                    content=incoming_content,
                    content_type=getattr(message, 'format', None) or getattr(message, 'subformat', None) or 'text',
                    metadata_=(msg_meta if isinstance(msg_meta, dict) else None),
                )
                session.add(incoming_msg)
                # update conversation activity
                conv.last_activity_at = func.now()
                session.add(conv)
                await session.commit()
                await session.refresh(incoming_msg)
                # ensure session manager tracks this conversation as last active
                try:
                    setattr(manager, 'last_conversation_id', conv.id)
                except Exception:
                    pass
                # If this conversation was just created, set its title from the first user message
                if created_conv:
                    try:
                        snippet = (incoming_content or "").strip().splitlines()[0][:120]
                        if snippet:
                            conv.title = snippet
                            session.add(conv)
                            await session.commit()
                            await session.refresh(conv)
                    except Exception:
                        logger.exception("Failed to set conversation title from first message")

            try:
                msg_dict = message.to_dict() if hasattr(message, "to_dict") else message.model_dump()
                fmt = msg_dict.get("format")
                subfmt = msg_dict.get("subformat")
                content_len = len(str(msg_dict.get("content") or "")) if isinstance(msg_dict, dict) else 0
                submsgs = msg_dict.get("submessages") or msg_dict.get("messages") or []
                logger.debug(
                    "NLIP /nlip received",
                    extra={
                        "format": fmt,
                        "subformat": subfmt,
                        "content_len": content_len,
                        "submessages_count": len(submsgs) if hasattr(submsgs, "__len__") else 0,
                        "submessage_formats": [
                            (sm.get("format"), sm.get("subformat")) for sm in submsgs if isinstance(sm, dict)
                        ],
                    },
                )
            except Exception:
                logger.debug("NLIP /nlip received (logging failed)")
            try:
                response = await manager.process_nlip(message)
            except Exception as e:
                logger.error(f"Error processing NLIP message: {str(e)}")
                traceback.print_exc(file=sys.stderr)
                # on error, still return a 400 to client
                raise HTTPException(status_code=400, detail=str(e))

            # persist assistant response into messages table
            try:
                # attempt to extract response metadata and content
                resp_meta = None
                try:
                    resp_meta = getattr(response, 'metadata', None) or getattr(response, 'metadata_', None)
                except Exception:
                    resp_meta = None

                try:
                    assistant_content = getattr(response, 'content', None)
                    if assistant_content is None:
                        assistant_content = str(response)
                except Exception:
                    assistant_content = str(response)

                async with AsyncSessionLocal() as session:
                    assistant_msg = Message(
                        conversation_id=conv.id,
                        sender_id=None,
                        role='assistant',
                        content=assistant_content,
                        content_type=getattr(response, 'format', None) or getattr(response, 'subformat', None) or 'text',
                        metadata_=(resp_meta if isinstance(resp_meta, dict) else None),
                    )
                    session.add(assistant_msg)
                    conv.last_activity_at = func.now()
                    session.add(conv)
                    await session.commit()
                    await session.refresh(assistant_msg)
            except Exception:
                logger.exception("Failed to persist assistant message for NLIP response")

            # Always normalize the manager response into a JSON-serializable dict
            resp_body = None
            try:
                if isinstance(response, dict):
                    resp_body = dict(response)
                else:
                    if hasattr(response, 'to_dict'):
                        try:
                            resp_body = response.to_dict()
                        except Exception:
                            resp_body = None
                    if resp_body is None and hasattr(response, 'dict'):
                        try:
                            resp_body = response.dict()
                        except Exception:
                            resp_body = None
                    if resp_body is None:
                        try:
                            resp_body = dict(getattr(response, '__dict__', {}) or {})
                        except Exception:
                            resp_body = None
            except Exception:
                resp_body = None

            if resp_body is None:
                try:
                    resp_body = { 'content': getattr(response, 'content', str(response)) }
                except Exception:
                    resp_body = { 'content': str(response) }

            if created_conv:
                try:
                    resp_body['conversation_id'] = str(conv.id)
                except Exception:
                    logger.exception("Failed to attach conversation_id to NLIP response")

            return resp_body
            
        @app.get("/health")
        async def health_check():
            return {"status": "ok"}
        
        class UserCreate(BaseModel):
            name: str
            email: EmailStr
            password: str
            location: Optional[str] = None
            
        @app.post("/signup")
        async def signup(user: UserCreate, request: Request, response: Response):
            """
            Expects JSON: {"email": "...", "password": "...", "location": "..."}
            """
            try:
                # pass name through to create_user (create_user signature updated)
                created = await create_user(email=user.email, password=user.password, location=user.location, name=user.name)
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
            return {
                "message": "Signed up",
                "session_id": session_id,
                "user_id": created.id,
                "email": created.email,
                "name": getattr(created, 'name', None),
                "location": getattr(created, 'location', None),
            }

        @app.get("/me")
        async def get_me(request: Request):
            # Return current user's profile based on session cookie
            session_id = request.cookies.get(self.session_cookie_name)
            if not session_id or session_id not in self.sessions:
                raise HTTPException(status_code=401, detail="Not authenticated")
            manager = self.sessions[session_id]
            user_id = getattr(manager, 'user_id', None)
            if not user_id:
                raise HTTPException(status_code=401, detail="Not authenticated")
            user = await get_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return {
                "user_id": str(user.id),
                "name": getattr(user, 'name', None),
                "email": user.email,
                "location": getattr(user, 'location', None),
                "phone_number": getattr(user, 'phone_number', None),
                "country_code": getattr(user, 'country_code', None),
                "avatar_uri": getattr(user, 'avatar_uri', None),
            }

        class UserUpdate(BaseModel):
            name: Optional[str] = None
            location: Optional[str] = None
            phone_number: Optional[str] = None
            country_code: Optional[str] = None
            avatar_uri: Optional[str] = None

        @app.put("/me")
        async def update_me(payload: UserUpdate, request: Request):
            session_id = request.cookies.get(self.session_cookie_name)
            if not session_id or session_id not in self.sessions:
                raise HTTPException(status_code=401, detail="Not authenticated")
            manager = self.sessions[session_id]
            user_id = getattr(manager, 'user_id', None)
            if not user_id:
                raise HTTPException(status_code=401, detail="Not authenticated")
            # update fields
            updated = await update_user(user_id, **payload.dict())
            if not updated:
                raise HTTPException(status_code=404, detail="User not found")
            return {
                "user_id": str(updated.id),
                "name": getattr(updated, 'name', None),
                "email": updated.email,
                "location": getattr(updated, 'location', None),
                "phone_number": getattr(updated, 'phone_number', None),
                "country_code": getattr(updated, 'country_code', None),
                "avatar_uri": getattr(updated, 'avatar_uri', None),
            }

        @app.post("/login")
        async def login(payload: dict, request: Request, response: Response):
            """
            Expects JSON: {"email": "...", "password": "..."}
            """
            from app.models.user import User
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
                "name": getattr(user, "name", None),
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

        # === Conversations & Messages endpoints ===
        class ConversationCreate(BaseModel):
            title: Optional[str] = None
            metadata: Optional[dict] = None

        class MessageCreate(BaseModel):
            sender_id: Optional[str] = None
            role: str
            content: Optional[str] = None
            content_type: Optional[str] = "text"
            metadata: Optional[dict] = None
            reply_to_id: Optional[str] = None

        @app.post("/conversations")
        async def create_conversation(payload: ConversationCreate, request: Request):
            from app.models.conversation import Conversation
            from app.auth.db import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                # Try to associate conversation with authenticated user (created_by)
                created_by = None
                try:
                    session_id = request.cookies.get(self.session_cookie_name)
                    if session_id and session_id in self.sessions:
                        manager = self.sessions[session_id]
                        created_by = getattr(manager, 'user_id', None)
                except Exception:
                    created_by = None

                conv = Conversation(title=payload.title, created_by=(created_by if created_by is not None else None), metadata_=payload.metadata)
                session.add(conv)
                await session.commit()
                await session.refresh(conv)
                # If a session exists for the request, mark this as the last active conversation
                try:
                    session_id = request.cookies.get(self.session_cookie_name)
                    if session_id and session_id in self.sessions:
                        setattr(self.sessions[session_id], 'last_conversation_id', conv.id)
                except Exception:
                    pass
                return {
                    "id": str(conv.id),
                    "title": conv.title,
                    "metadata": conv.metadata_,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                }

        @app.get("/conversations")
        async def list_conversations(request: Request, limit: int = 50, include_archived: bool = False):
            """List recent conversations for the currently authenticated session (created_by).
            If not authenticated, returns recent conversations ordered by last_activity_at.
            """
            from app.models.conversation import Conversation
            from app.auth.db import AsyncSessionLocal
            from sqlalchemy import select, desc

            session_id = request.cookies.get(self.session_cookie_name)
            manager = None
            user_id = None
            if session_id and session_id in self.sessions:
                manager = self.sessions[session_id]
                user_id = getattr(manager, 'user_id', None)

            async with AsyncSessionLocal() as session:
                q = select(Conversation)
                if user_id:
                    q = q.where(Conversation.created_by == user_id)
                # By default, filter out archived conversations unless the client requests them
                if not include_archived:
                    q = q.where(Conversation.is_archived == False)
                q = q.order_by(desc(Conversation.last_activity_at)).limit(limit)
                result = await session.execute(q)
                rows = result.scalars().all()
                out = []
                for c in rows:
                    out.append({
                        "id": str(c.id),
                        "title": c.title,
                        "metadata": c.metadata_,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
                    })
                return {"conversations": out}

        @app.get("/conversations/{conversation_id}")
        async def get_conversation(conversation_id: str):
            from app.models.conversation import Conversation
            from app.auth.db import AsyncSessionLocal
            import uuid as _uuid

            try:
                conv_id = _uuid.UUID(conversation_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid conversation id")

            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                result = await session.execute(select(Conversation).where(Conversation.id == conv_id))
                conv = result.scalars().one_or_none()
                if not conv:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                return {
                    "id": str(conv.id),
                    "title": conv.title,
                    "metadata": conv.metadata_,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "last_activity_at": conv.last_activity_at.isoformat() if conv.last_activity_at else None,
                }

        @app.post("/conversations/{conversation_id}/messages")
        async def post_message(conversation_id: str, payload: MessageCreate, request: Request):
            from app.models.message import Message
            from app.models.conversation import Conversation
            from app.auth.db import AsyncSessionLocal
            import uuid as _uuid

            try:
                conv_id = _uuid.UUID(conversation_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid conversation id")

            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                result = await session.execute(select(Conversation).where(Conversation.id == conv_id))
                conv = result.scalars().one_or_none()
                if not conv:
                    raise HTTPException(status_code=404, detail="Conversation not found")

                msg = Message(
                    conversation_id=conv_id,
                    sender_id=payload.sender_id,
                    role=payload.role,
                    content=payload.content,
                    content_type=payload.content_type,
                    metadata_=payload.metadata,
                    reply_to_id=payload.reply_to_id,
                )
                session.add(msg)
                # update conversation last activity
                conv.last_activity_at = func.now()
                session.add(conv)
                await session.commit()
                await session.refresh(msg)
                # Update session manager to mark this as last active conversation for this session
                try:
                    session_id = request.cookies.get(self.session_cookie_name)
                    if session_id and session_id in self.sessions:
                        setattr(self.sessions[session_id], 'last_conversation_id', conv_id)
                except Exception:
                    pass
                return {
                    "id": str(msg.id),
                    "conversation_id": str(msg.conversation_id),
                    "sender_id": str(msg.sender_id) if msg.sender_id else None,
                    "role": msg.role,
                    "content": msg.content,
                    "content_type": msg.content_type,
                    "metadata": msg.metadata_,
                    "reply_to_id": str(msg.reply_to_id) if msg.reply_to_id else None,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }

        @app.get("/conversations/{conversation_id}/messages")
        async def get_messages(conversation_id: str, limit: int = 50, cursor: Optional[str] = None):
            """
            Cursor format: '<created_at_iso>|<message_id>' where created_at_iso is ISO format with timezone (UTC Z allowed).
            If no cursor is provided, returns the latest `limit` messages (newest first).
            """
            from app.models.message import Message
            from app.auth.db import AsyncSessionLocal
            import uuid as _uuid
            from sqlalchemy import select, and_, or_, desc
            from datetime import datetime

            try:
                conv_id = _uuid.UUID(conversation_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid conversation id")

            parsed_cursor = None
            if cursor:
                try:
                    created_at_str, mid = cursor.split("|", 1)
                    # accept trailing Z as UTC indicator
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str.replace("Z", "+00:00")
                    cursor_ts = datetime.fromisoformat(created_at_str)
                    cursor_id = _uuid.UUID(mid)
                    parsed_cursor = (cursor_ts, cursor_id)
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid cursor format")

            async with AsyncSessionLocal() as session:
                q = select(Message).where(Message.conversation_id == conv_id)
                if parsed_cursor:
                    cursor_ts, cursor_id = parsed_cursor
                    q = q.where(
                        or_(
                            Message.created_at < cursor_ts,
                            and_(Message.created_at == cursor_ts, Message.id < cursor_id),
                        )
                    )
                q = q.order_by(desc(Message.created_at), desc(Message.id)).limit(limit)
                result = await session.execute(q)
                rows = result.scalars().all()

                # prepare next cursor if we have a full page
                next_cursor = None
                if rows and len(rows) >= limit:
                    last = rows[-1]
                    ts = last.created_at.isoformat()
                    if ts.endswith('+00:00'):
                        ts = ts.replace('+00:00', 'Z')
                    next_cursor = f"{ts}|{last.id}"

                # return chronological order (oldest first)
                rows.reverse()
                out = []
                for m in rows:
                    out.append({
                        "id": str(m.id),
                        "conversation_id": str(m.conversation_id),
                        "sender_id": str(m.sender_id) if m.sender_id else None,
                        "role": m.role,
                        "content": m.content,
                        "content_type": m.content_type,
                        "metadata": m.metadata_,
                        "reply_to_id": str(m.reply_to_id) if m.reply_to_id else None,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    })

                return {"messages": out, "next_cursor": next_cursor}
            
        @app.post("/conversations/{conversation_id}/archive")
        async def archive_conversation(conversation_id: str, request: Request):
            """Mark a conversation as archived (sets `is_archived` = True).
            Returns the conversation id and new archived flag on success.
            """
            from app.models.conversation import Conversation
            from app.auth.db import AsyncSessionLocal
            import uuid as _uuid
            from sqlalchemy import select

            try:
                conv_id = _uuid.UUID(conversation_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid conversation id")

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Conversation).where(Conversation.id == conv_id))
                conv = result.scalars().one_or_none()
                if not conv:
                    raise HTTPException(status_code=404, detail="Conversation not found")

                try:
                    conv.is_archived = True
                    session.add(conv)
                    await session.commit()
                    await session.refresh(conv)
                except Exception:
                    logger.exception("Failed to archive conversation")
                    raise HTTPException(status_code=500, detail="Failed to archive conversation")

                # If this conversation was the session's last active conversation, clear it
                try:
                    session_id = request.cookies.get(self.session_cookie_name)
                    if session_id and session_id in self.sessions:
                        mgr = self.sessions[session_id]
                        if getattr(mgr, 'last_conversation_id', None) == conv.id:
                            try:
                                setattr(mgr, 'last_conversation_id', None)
                            except Exception:
                                pass
                except Exception:
                    # non-fatal
                    pass

                return {"id": str(conv.id), "is_archived": True}
            
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
