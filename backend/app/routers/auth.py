"""
Authentication router.

Handles Google OAuth login flow, session management, and user info endpoints.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.auth.jwt import create_access_token, decode_token, TokenExpiredError, TokenInvalidError
from app.auth.oauth import (
    OAuthCodeExchangeError,
    OAuthRefreshError,
    OAuthUserInfoError,
    exchange_code_for_token,
    get_google_auth_url,
    get_user_info,
    refresh_access_token,
)
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.repositories import user_repo
from app.utils.timestamp import utc_now

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
    with get_db() as conn:
        db_user = user_repo.create_user(conn, user)
        # Update last login timestamp
        user_repo.update_last_login(conn, db_user.id)

        # Store refresh token if provided (for silent re-auth)
        google_refresh_token = token_response.get("refresh_token")
        if google_refresh_token:
            # Google refresh tokens don't have a set expiry, but we set a long one
            # They can be invalidated by user revoking access or password change
            refresh_expires_at = utc_now() + timedelta(days=365)
            user_repo.update_refresh_token(
                conn, db_user.id, google_refresh_token, refresh_expires_at
            )

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
async def logout(request: Request) -> JSONResponse:
    """
    Log out by clearing authentication cookie and refresh token.

    Returns:
        JSON response confirming logout with cookie cleared
    """
    # Clear refresh token from database if user is authenticated
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        try:
            token_data = decode_token(token)
            with get_db() as conn:
                db_user = user_repo.get_user_by_email(conn, token_data.email)
                if db_user:
                    user_repo.clear_refresh_token(conn, db_user.id)
        except (TokenExpiredError, TokenInvalidError):
            pass  # Token invalid, just clear the cookie

    response = JSONResponse(content={"success": True})

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


@router.post("/refresh")
async def refresh_token(request: Request) -> JSONResponse:
    """
    Silent token refresh endpoint.

    Uses stored Google refresh token to:
    1. Get new Google access token
    2. Verify user still valid
    3. Issue new JWT
    4. Set new cookie

    Returns:
        JSON response with success status and new JWT cookie
    """
    # Get current token to identify user
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token",
        )

    # Decode token (allow expired tokens for refresh)
    try:
        token_data = decode_token(token)
    except TokenExpiredError:
        # Token expired but we can still extract the email
        # Re-decode without verification
        from jose import jwt
        payload = jwt.get_unverified_claims(token)
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    else:
        email = token_data.email

    # Get user and their refresh token
    with get_db() as conn:
        db_user = user_repo.get_user_by_email(conn, email)

        if not db_user or not db_user.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token available",
            )

        # Use Google refresh token to get new access token
        try:
            google_token_response = await refresh_access_token(db_user.refresh_token)
        except OAuthRefreshError as e:
            # Clear invalid refresh token
            user_repo.clear_refresh_token(conn, db_user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token refresh failed: {e}",
            )

        # Verify user is still valid with Google
        new_access_token = google_token_response.get("access_token")
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token from refresh",
            )

        try:
            user_info = await get_user_info(new_access_token)
        except OAuthUserInfoError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to verify user: {e}",
            )

        # Update last login
        user_repo.update_last_login(conn, db_user.id)

        # If Google returned a new refresh token, store it
        new_refresh_token = google_token_response.get("refresh_token")
        if new_refresh_token:
            refresh_expires_at = utc_now() + timedelta(days=365)
            user_repo.update_refresh_token(
                conn, db_user.id, new_refresh_token, refresh_expires_at
            )

    # Create new JWT token
    jwt_token = create_access_token(db_user)

    # Create response with new cookie
    response = JSONResponse(content={"success": True})

    max_age = settings.jwt_expiry_hours * 3600
    cookie_kwargs = {
        "key": AUTH_COOKIE_NAME,
        "value": jwt_token,
        "max_age": max_age,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        cookie_kwargs["domain"] = settings.cookie_domain
    response.set_cookie(**cookie_kwargs)

    return response
