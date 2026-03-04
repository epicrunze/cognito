"""JWT token utilities — ported from archive unchanged."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings
from app.models.user import TokenData, User

ALGORITHM = "HS256"


class TokenError(Exception):
    """Base exception for token errors."""


class TokenExpiredError(TokenError):
    """Token has expired."""


class TokenInvalidError(TokenError):
    """Token is invalid (bad signature, malformed, etc.)."""


def create_access_token(user: User) -> str:
    """Generate JWT token for authenticated user."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    """
    Validate and decode JWT token.

    Raises:
        TokenExpiredError: If token has expired.
        TokenInvalidError: If token is malformed or has invalid signature.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return TokenData(
            email=payload.get("email"),
            name=payload.get("name"),
            picture=payload.get("picture"),
            exp=payload.get("exp"),
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except JWTError as e:
        raise TokenInvalidError(f"Invalid token: {e}")
