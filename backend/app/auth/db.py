import os
import logging
from typing import Optional
import bcrypt

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/nlip_db")

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

logger = logging.getLogger("auth.db")


async def init_db(retries: int = 5, initial_delay: float = 1.0) -> None:
    """Create tables (runs Base.metadata.create_all) with simple retry/backoff."""
    from asyncio import sleep
    from app.models.base import Base
    # ensure model modules are imported so their declarative classes register with Base.metadata
    # (otherwise Base.metadata.create_all won't see models that haven't been imported)
    try:
        import app.models.user  # noqa: F401
        import app.models.conversation  # noqa: F401
        import app.models.message  # noqa: F401
    except Exception:
        logger.exception("One or more model modules failed to import before create_all")

    # Log which tables have been registered on Base.metadata
    try:
        table_names = list(Base.metadata.tables.keys())
        logger.info("Registered declarative tables: %s", table_names)
    except Exception:
        logger.exception("Failed to enumerate Base.metadata tables")

    delay = initial_delay
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            print(DATABASE_URL)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created or already exist.")
            # After create_all, verify expected tables exist in the DB
            try:
                from sqlalchemy import text
                async with engine.begin() as conn2:
                    res = await conn2.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users','conversations','messages')"))
                    found = [row[0] for row in res.fetchall()]
                    logger.info("Post-create_all: existing tables (subset): %s", found)
            except Exception:
                logger.exception("Failed to verify created tables in information_schema")
            return
        except Exception as exc:
            last_exc = exc
            logger.warning("init_db attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                await sleep(delay)
                delay *= 2
    logger.error("All init_db attempts failed.")
    raise last_exc


async def create_user(email: str, password: str, location: Optional[str] = None, name: Optional[str] = None):
    """
    Create a new user row and return the ORM object.
    Raises sqlalchemy.exc.IntegrityError on duplicate email.
    """
    import uuid    
    from app.models.user import User
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Ensure name is stored (models.User.name is non-nullable)
    user = User(id=uuid.uuid4(), email=email, password=password_hash, location=location, name=(name or ""))

    async with AsyncSessionLocal() as session:
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()
            raise

async def get_user_by_email(email: str):
    """Retrieve a user by email. Returns None if not found."""
    from app.models.user import User

    # Use SQLAlchemy ORM select so we get an ORM `User` instance
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().one_or_none()
        return user


async def get_user_by_id(user_id):
    """Retrieve a user by id (UUID or string). Returns None if not found."""
    from app.models.user import User
    import uuid as _uuid

    # normalize uuid
    if isinstance(user_id, str):
        try:
            user_id = _uuid.UUID(user_id)
        except Exception:
            pass

    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().one_or_none()
        return user


async def update_user(user_id, **fields):
    """Update user fields and return the refreshed user object."""
    from app.models.user import User
    import uuid as _uuid

    if isinstance(user_id, str):
        try:
            user_id = _uuid.UUID(user_id)
        except Exception:
            pass

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().one_or_none()
        if not user:
            return None

        # Only set attributes that exist on the model
        for k, v in fields.items():
            if v is None:
                continue
            if hasattr(user, k):
                setattr(user, k, v)

        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False