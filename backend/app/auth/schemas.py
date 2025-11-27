from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    location: Optional[str] = None

class UserRead(BaseModel):
    id: int
    email: EmailStr
    location: Optional[str] = None

    class Config:
        orm_mode = True
