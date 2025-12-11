"""
Authentication dependencies for FastAPI.

Provides dependency injection for protected routes.
"""

from fastapi import HTTPException, Request, status

from app.auth.jwt import TokenError, TokenExpiredError, TokenInvalidError, decode_token
from app.models.user import User

# Cookie name for JWT token
AUTH_COOKIE_NAME = "cognito_auth"


async def get_current_user(request: Request) -> User:
    """
    FastAPI dependency to get current authenticated user.

    Extracts JWT from HttpOnly cookie, validates it, and returns user info.

    Args:
        request: FastAPI request object

    Returns:
        User object with email, name, picture

    Raises:
        HTTPException 401: If token is missing, expired, or invalid
    """
    token = request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = decode_token(token)
        return User(
            email=token_data.email,
            name=token_data.name,
            picture=token_data.picture,
        )
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
