import os
import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("NLIP.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/nlip_db",
)

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(retries: int = 5, initial_delay: float = 1.0) -> None:
    """Initialize database tables with retry/backoff.

    This imports the SQLAlchemy `Base` lazily to avoid import cycles.
    Retries when connection fails, then raises the last exception so calling
    code can fail fast if desired.
    """
    delay = initial_delay
    last_exc: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        try:
            logger.info("Attempting to create DB tables (attempt %s/%s)", attempt, retries)
            # import Base lazily from the auth subpackage where models are defined
            from app.auth.models import Base

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database tables created or already exist.")
            return
        except Exception as exc:  # noqa: BLE001 - Broad except is intentional for retry logic
            last_exc = exc
            logger.warning("Database init attempt %s failed: %s", attempt, exc)
            if attempt < retries:
                logger.info("Retrying in %.1f seconds...", delay)
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.exception("All database init attempts failed.")
    # If we exit loop without returning, raise last exception
    if last_exc:
        raise last_exc
