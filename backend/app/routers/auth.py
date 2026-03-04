"""Auth router — full Google OAuth flow with JWT cookies and refresh tokens."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.auth.jwt import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_token,
)
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


def _set_auth_cookie(response, jwt_token: str) -> None:
    """Helper: attach JWT as HttpOnly cookie."""
    max_age = settings.jwt_expiry_hours * 3600
    kwargs = {
        "key": AUTH_COOKIE_NAME,
        "value": jwt_token,
        "max_age": max_age,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.set_cookie(**kwargs)


def _delete_auth_cookie(response) -> None:
    """Helper: delete the auth cookie."""
    kwargs = {
        "key": AUTH_COOKIE_NAME,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    response.delete_cookie(**kwargs)


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect to Google OAuth consent screen."""
    return RedirectResponse(url=get_google_auth_url())


@router.get("/callback")
async def oauth_callback(code: str | None = None) -> RedirectResponse:
    """
    Google OAuth callback.

    Exchanges code for tokens, validates email, creates/updates user in DB,
    and sets JWT as HttpOnly cookie.
    """
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code")

    try:
        token_response = await exchange_code_for_token(code)
    except OAuthCodeExchangeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid authorization code: {e}")

    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token received")

    try:
        user_info = await get_user_info(access_token)
    except OAuthUserInfoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to fetch user info: {e}")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No email in user info")

    if settings.allowed_email and email.lower() != settings.allowed_email.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not authorized")

    user = User(email=email, name=user_info.get("name", ""), picture=user_info.get("picture"))

    with get_db() as conn:
        db_user = user_repo.create_user(conn, user)
        user_repo.update_last_login(conn, db_user.id)

        google_refresh_token = token_response.get("refresh_token")
        if google_refresh_token:
            refresh_expires_at = utc_now() + timedelta(days=365)
            user_repo.update_refresh_token(conn, db_user.id, google_refresh_token, refresh_expires_at)

    jwt_token = create_access_token(db_user)
    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)
    _set_auth_cookie(response, jwt_token)
    return response


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return current authenticated user info."""
    return current_user


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    """Clear JWT cookie and remove refresh token from DB."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        try:
            token_data = decode_token(token)
            with get_db() as conn:
                db_user = user_repo.get_user_by_email(conn, token_data.email)
                if db_user:
                    user_repo.clear_refresh_token(conn, db_user.id)
        except (TokenExpiredError, TokenInvalidError):
            pass

    response = JSONResponse(content={"success": True})
    _delete_auth_cookie(response)
    return response


@router.post("/refresh")
async def refresh_token(request: Request) -> JSONResponse:
    """
    Silent token refresh using stored Google refresh token.

    Accepts even expired JWTs (to extract the email), then uses the stored
    Google refresh token to get a new access token and issue a new JWT.
    """
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authentication token")

    try:
        token_data = decode_token(token)
        email = token_data.email
    except TokenExpiredError:
        from jose import jwt as jose_jwt
        payload = jose_jwt.get_unverified_claims(token)
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except TokenInvalidError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    with get_db() as conn:
        db_user = user_repo.get_user_by_email(conn, email)
        if not db_user or not db_user.refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token available")

        try:
            google_token_response = await refresh_access_token(db_user.refresh_token)
        except OAuthRefreshError as e:
            user_repo.clear_refresh_token(conn, db_user.id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token refresh failed: {e}")

        new_access_token = google_token_response.get("access_token")
        if not new_access_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No access token from refresh")

        try:
            await get_user_info(new_access_token)
        except OAuthUserInfoError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Failed to verify user: {e}")

        user_repo.update_last_login(conn, db_user.id)

        new_refresh_token = google_token_response.get("refresh_token")
        if new_refresh_token:
            refresh_expires_at = utc_now() + timedelta(days=365)
            user_repo.update_refresh_token(conn, db_user.id, new_refresh_token, refresh_expires_at)

    jwt_token = create_access_token(db_user)
    response = JSONResponse(content={"success": True})
    _set_auth_cookie(response, jwt_token)
    return response
