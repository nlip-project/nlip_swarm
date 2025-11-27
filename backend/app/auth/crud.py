from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
import hashlib
from .models import User

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, email: str, password: str, location: str | None = None) -> User:
    try:
        hashed = pwd_context.hash(password)
    except ValueError:
        # Fallback for backends that enforce a max password byte length
        # Pre-hash with SHA-256 (32 bytes) so bcrypt backends won't error.
        pre_hashed = hashlib.sha256(password.encode()).hexdigest()
        hashed = pwd_context.hash(pre_hashed)
    user = User(email=email, password_hash=hashed, location=location)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        await db.rollback()
        raise

async def verify_password(plain_password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed)
    except ValueError:
        # If the stored hash was created via a backend that raised on long
        # inputs, try verifying against a SHA-256 pre-hash (the same
        # transformation used in create_user fallback).
        try:
            pre_hashed = hashlib.sha256(plain_password.encode()).hexdigest()
            return pwd_context.verify(pre_hashed, hashed)
        except Exception:
            return False
    except Exception:
        return False

async def update_user(db: AsyncSession, user_id: int, **fields) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    for k, v in fields.items():
        if hasattr(user, k) and v is not None:
            setattr(user, k, v)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await get_user(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True
