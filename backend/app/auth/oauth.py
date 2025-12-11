"""
Google OAuth 2.0 utilities.

Handles OAuth flow: generating auth URLs, exchanging codes for tokens,
and fetching user info from Google.
"""

from urllib.parse import urlencode

import httpx

from app.config import settings

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class OAuthError(Exception):
    """Base exception for OAuth errors."""

    pass


class OAuthCodeExchangeError(OAuthError):
    """Failed to exchange authorization code for tokens."""

    pass


class OAuthUserInfoError(OAuthError):
    """Failed to fetch user info from OAuth provider."""

    pass


def get_google_auth_url(state: str | None = None) -> str:
    """
    Generate Google OAuth consent screen URL.

    Args:
        state: Optional state parameter for CSRF protection

    Returns:
        Full URL to redirect user to Google's OAuth consent screen
    """
    redirect_uri = f"{settings.frontend_url}/auth/callback"

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    if state:
        params["state"] = state

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """
    Exchange authorization code for access token.

    Args:
        code: Authorization code from Google callback

    Returns:
        Token response containing access_token, refresh_token, etc.

    Raises:
        OAuthCodeExchangeError: If token exchange fails
    """
    redirect_uri = f"{settings.frontend_url}/auth/callback"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                raise OAuthCodeExchangeError(
                    f"Token exchange failed: {response.status_code} {response.text}"
                )

            return response.json()

        except httpx.RequestError as e:
            raise OAuthCodeExchangeError(f"Network error during token exchange: {e}")


async def get_user_info(access_token: str) -> dict:
    """
    Fetch user profile from Google.

    Args:
        access_token: Valid Google access token

    Returns:
        User info dict with email, name, picture, etc.

    Raises:
        OAuthUserInfoError: If fetching user info fails
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise OAuthUserInfoError(
                    f"Failed to get user info: {response.status_code} {response.text}"
                )

            return response.json()

        except httpx.RequestError as e:
            raise OAuthUserInfoError(f"Network error fetching user info: {e}")
