"""
User models for authentication.

Pydantic models for user data representation and JWT token payload.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """Basic user information from OAuth provider."""

    email: EmailStr
    name: str
    picture: Optional[str] = None


class UserInDB(User):
    """User with database fields."""

    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    """JWT token payload schema."""

    email: EmailStr
    name: str
    picture: Optional[str] = None
    exp: Optional[datetime] = None
