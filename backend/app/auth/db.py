import os
import logging
from typing import Optional
import bcrypt

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

DATABASE_URL = os.getenv(
    "DATABASE_URL")

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

logger = logging.getLogger("auth.db")


async def init_db(retries: int = 5, initial_delay: float = 1.0) -> None:
    """Create tables (runs Base.metadata.create_all) with simple retry/backoff."""
    from asyncio import sleep
    from app.auth.models import Base

    delay = initial_delay
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created or already exist.")
            return
        except Exception as exc:
            last_exc = exc
            logger.warning("init_db attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                await sleep(delay)
                delay *= 2
    logger.error("All init_db attempts failed.")
    raise last_exc


async def create_user(email: str, password: str, location: Optional[str] = None):
    """
    Create a new user row and return the ORM object.
    Raises sqlalchemy.exc.IntegrityError on duplicate email.
    """
    import uuid    
    from app.auth.models import User
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user = User(id=uuid.uuid4(), email=email, password=password_hash, location=location)

    async with AsyncSessionLocal() as session:
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()
            raise


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False