"""
Authentication router.

Handles Google OAuth login flow, session management, and user info endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.auth.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.auth.jwt import create_access_token
from app.auth.oauth import (
    OAuthCodeExchangeError,
    OAuthUserInfoError,
    exchange_code_for_token,
    get_google_auth_url,
    get_user_info,
)
from app.config import settings
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login")
async def login() -> RedirectResponse:
    """
    Initiate Google OAuth login flow.

    Redirects user to Google's OAuth consent screen.
    """
    auth_url = get_google_auth_url()
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def oauth_callback(
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """
    Handle OAuth callback from Google.

    Verifies the authorization code, checks email against allowed list,
    and sets JWT cookie on success.

    Query Params:
        code: Authorization code from Google
        error: Error message if user cancelled or other OAuth error

    Returns:
        Redirect to frontend with success or error
    """
    # Handle user cancellation or OAuth error
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    # Missing code is a bad request
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )

    # Exchange code for token
    try:
        token_response = await exchange_code_for_token(code)
    except OAuthCodeExchangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid authorization code: {e}",
        )

    # Get user info from Google
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received",
        )

    try:
        user_info = await get_user_info(access_token)
    except OAuthUserInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch user info: {e}",
        )

    # Verify email is in allowed list
    email = user_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email in user info",
        )

    if settings.allowed_email and email.lower() != settings.allowed_email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not authorized",
        )

    # Create user object
    user = User(
        email=email,
        name=user_info.get("name", ""),
        picture=user_info.get("picture"),
    )

    # Create or update user in database
    from app.database import get_db
    from app.repositories import user_repo

    with get_db() as conn:
        db_user = user_repo.create_user(conn, user)
        # Update last login timestamp
        user_repo.update_last_login(conn, db_user.id)

    # Create JWT token
    jwt_token = create_access_token(db_user)

    # Redirect to frontend with cookie
    response = RedirectResponse(
        url=settings.frontend_url,
        status_code=status.HTTP_302_FOUND,
    )

    # Set HttpOnly cookie with JWT
    max_age = settings.jwt_expiry_hours * 3600  # Convert hours to seconds
    cookie_kwargs = {
        "key": AUTH_COOKIE_NAME,
        "value": jwt_token,
        "max_age": max_age,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    # Add domain only if configured (for subdomain sharing)
    if settings.cookie_domain:
        cookie_kwargs["domain"] = settings.cookie_domain
    response.set_cookie(**cookie_kwargs)

    return response


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated user info.

    Returns:
        User object with email, name, picture
    """
    return current_user


@router.post("/logout")
async def logout() -> RedirectResponse:
    """
    Log out by clearing authentication cookie.

    Returns:
        Redirect to frontend login page with cookie cleared
    """
    response = RedirectResponse(
        url=f"{settings.frontend_url}/login",
        status_code=status.HTTP_302_FOUND,
    )

    # Clear the auth cookie
    delete_kwargs = {
        "key": AUTH_COOKIE_NAME,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        delete_kwargs["domain"] = settings.cookie_domain
    response.delete_cookie(**delete_kwargs)

    return response
