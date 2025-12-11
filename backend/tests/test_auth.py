"""
Tests for authentication endpoints.

Tests OAuth flow, email restriction, and protected routes with mocked Google OAuth.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.auth.dependencies import AUTH_COOKIE_NAME
from app.auth.jwt import ALGORITHM
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("app.auth.oauth.settings") as oauth_settings, \
         patch("app.auth.jwt.settings") as jwt_settings, \
         patch("app.routers.auth.settings") as router_settings:
        
        # Common settings
        for settings in [oauth_settings, jwt_settings, router_settings]:
            settings.google_client_id = "test-client-id"
            settings.google_client_secret = "test-client-secret"
            settings.frontend_url = "http://localhost:5173"
            settings.jwt_secret = "test-jwt-secret"
            settings.jwt_expiry_hours = 24
            settings.allowed_email = "allowed@example.com"
            settings.cookie_secure = False
        
        yield {
            "oauth": oauth_settings,
            "jwt": jwt_settings,
            "router": router_settings,
        }


@pytest.fixture
def valid_token(mock_settings) -> str:
    """Generate a valid JWT token for testing."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "email": "allowed@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "exp": expire,
    }
    return jwt.encode(
        payload,
        mock_settings["jwt"].jwt_secret,
        algorithm=ALGORITHM,
    )


@pytest.fixture
def expired_token(mock_settings) -> str:
    """Generate an expired JWT token for testing."""
    expire = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "email": "allowed@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "exp": expire,
    }
    return jwt.encode(
        payload,
        mock_settings["jwt"].jwt_secret,
        algorithm=ALGORITHM,
    )


class TestLoginEndpoint:
    """Tests for GET /api/auth/login."""

    def test_redirects_to_google(self, client: TestClient, mock_settings):
        """Should redirect to Google OAuth consent screen."""
        response = client.get("/api/auth/login", follow_redirects=False)

        assert response.status_code == 302
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "client_id=test-client-id" in location

    def test_includes_required_params(self, client: TestClient, mock_settings):
        """Redirect URL should include required OAuth params."""
        response = client.get("/api/auth/login", follow_redirects=False)

        location = response.headers["location"]
        assert "response_type=code" in location
        assert "scope=openid" in location


class TestCallbackEndpoint:
    """Tests for GET /api/auth/callback."""

    def test_handles_user_cancellation(self, client: TestClient, mock_settings):
        """Should redirect with error when user cancels OAuth."""
        response = client.get(
            "/api/auth/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "error=oauth_cancelled" in response.headers["location"]

    def test_returns_400_without_code(self, client: TestClient, mock_settings):
        """Should return 400 when no code provided."""
        response = client.get("/api/auth/callback")

        assert response.status_code == 400
        assert "Missing authorization code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_sets_cookie_on_success(self, client: TestClient, mock_settings):
        """Should set HttpOnly cookie on successful auth."""
        mock_token_response = {
            "access_token": "mock-access-token",
            "token_type": "Bearer",
        }
        mock_user_info = {
            "email": "allowed@example.com",
            "name": "Allowed User",
            "picture": "https://example.com/photo.jpg",
        }

        with patch("app.routers.auth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange, \
             patch("app.routers.auth.get_user_info", new_callable=AsyncMock) as mock_user:
            mock_exchange.return_value = mock_token_response
            mock_user.return_value = mock_user_info

            response = client.get(
                "/api/auth/callback",
                params={"code": "valid-auth-code"},
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert AUTH_COOKIE_NAME in response.cookies

    @pytest.mark.asyncio
    async def test_returns_403_for_non_allowed_email(self, client: TestClient, mock_settings):
        """Should return 403 when email not in allowed list."""
        mock_token_response = {
            "access_token": "mock-access-token",
            "token_type": "Bearer",
        }
        mock_user_info = {
            "email": "notallowed@example.com",
            "name": "Not Allowed User",
            "picture": None,
        }

        with patch("app.routers.auth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange, \
             patch("app.routers.auth.get_user_info", new_callable=AsyncMock) as mock_user:
            mock_exchange.return_value = mock_token_response
            mock_user.return_value = mock_user_info

            response = client.get(
                "/api/auth/callback",
                params={"code": "valid-auth-code"},
            )

            assert response.status_code == 403
            assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_code(self, client: TestClient, mock_settings):
        """Should return 400 when authorization code is invalid."""
        from app.auth.oauth import OAuthCodeExchangeError

        with patch("app.routers.auth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.side_effect = OAuthCodeExchangeError("Invalid code")

            response = client.get(
                "/api/auth/callback",
                params={"code": "invalid-code"},
            )

            assert response.status_code == 400
            assert "Invalid authorization code" in response.json()["detail"]


class TestMeEndpoint:
    """Tests for GET /api/auth/me."""

    def test_returns_user_with_valid_cookie(self, client: TestClient, valid_token: str, mock_settings):
        """Should return user info with valid auth cookie."""
        # Need to patch the dependency's settings access
        with patch("app.auth.dependencies.decode_token") as mock_decode:
            from app.models.user import TokenData
            mock_decode.return_value = TokenData(
                email="allowed@example.com",
                name="Test User",
                picture="https://example.com/photo.jpg",
            )
            
            client.cookies.set(AUTH_COOKIE_NAME, valid_token)
            response = client.get("/api/auth/me")

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "allowed@example.com"
            assert data["name"] == "Test User"
    
    def test_returns_401_without_cookie(self, client: TestClient, mock_settings):
        """Should return 401 when no auth cookie present."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_returns_401_with_expired_token(self, client: TestClient, expired_token: str, mock_settings):
        """Should return 401 when token is expired."""
        with patch("app.auth.jwt.settings") as jwt_settings:
            jwt_settings.jwt_secret = "test-jwt-secret"

            client.cookies.set(AUTH_COOKIE_NAME, expired_token)
            response = client.get("/api/auth/me")

            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()

    def test_returns_401_with_invalid_token(self, client: TestClient, mock_settings):
        """Should return 401 when token is invalid."""
        with patch("app.auth.jwt.settings") as jwt_settings:
            jwt_settings.jwt_secret = "test-jwt-secret"

            client.cookies.set(AUTH_COOKIE_NAME, "invalid-token")
            response = client.get("/api/auth/me")

            assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout."""

    def test_clears_cookie(self, client: TestClient, valid_token: str, mock_settings):
        """Should clear auth cookie on logout."""
        client.cookies.set(AUTH_COOKIE_NAME, valid_token)
        response = client.post(
            "/api/auth/logout",
            follow_redirects=False,
        )

        assert response.status_code == 302
        # Cookie should be deleted (set with empty value or max-age=0)
        assert AUTH_COOKIE_NAME in response.headers.get("set-cookie", "").lower()

    def test_redirects_to_login(self, client: TestClient, mock_settings):
        """Should redirect to login page after logout."""
        response = client.post("/api/auth/logout", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["location"]


class TestAllowedEmailCaseInsensitive:
    """Tests for case-insensitive email matching."""

    @pytest.mark.asyncio
    async def test_allows_different_case_email(self, client: TestClient, mock_settings):
        """Should allow email regardless of case."""
        mock_token_response = {
            "access_token": "mock-access-token",
            "token_type": "Bearer",
        }
        # Email with different case than allowed_email setting
        mock_user_info = {
            "email": "ALLOWED@EXAMPLE.COM",
            "name": "Allowed User",
            "picture": None,
        }

        with patch("app.routers.auth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange, \
             patch("app.routers.auth.get_user_info", new_callable=AsyncMock) as mock_user:
            mock_exchange.return_value = mock_token_response
            mock_user.return_value = mock_user_info

            response = client.get(
                "/api/auth/callback",
                params={"code": "valid-auth-code"},
                follow_redirects=False,
            )

            # Should succeed (302 redirect) not 403
            assert response.status_code == 302
            assert AUTH_COOKIE_NAME in response.cookies
