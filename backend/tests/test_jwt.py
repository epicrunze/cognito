"""
Tests for JWT token utilities.

Tests token generation, validation, expiry, and error handling.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from app.auth.jwt import (
    ALGORITHM,
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_token,
)
from app.models.user import User


@pytest.fixture
def test_user() -> User:
    """Sample user for testing."""
    return User(
        email="test@example.com",
        name="Test User",
        picture="https://example.com/photo.jpg",
    )


@pytest.fixture
def test_secret() -> str:
    """Test JWT secret."""
    return "test-secret-key-for-testing"


class TestCreateAccessToken:
    """Tests for create_access_token function."""

    def test_creates_valid_jwt(self, test_user: User, test_secret: str):
        """Token should be a valid JWT string."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(test_user)

            assert isinstance(token, str)
            # Should be decodable
            payload = jwt.decode(token, test_secret, algorithms=[ALGORITHM])
            assert payload is not None

    def test_includes_user_email(self, test_user: User, test_secret: str):
        """Token payload should include user email."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(test_user)
            payload = jwt.decode(token, test_secret, algorithms=[ALGORITHM])

            assert payload["email"] == test_user.email

    def test_includes_user_name(self, test_user: User, test_secret: str):
        """Token payload should include user name."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(test_user)
            payload = jwt.decode(token, test_secret, algorithms=[ALGORITHM])

            assert payload["name"] == test_user.name

    def test_includes_user_picture(self, test_user: User, test_secret: str):
        """Token payload should include user picture."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(test_user)
            payload = jwt.decode(token, test_secret, algorithms=[ALGORITHM])

            assert payload["picture"] == test_user.picture

    def test_includes_expiry(self, test_user: User, test_secret: str):
        """Token should have expiry claim."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(test_user)
            payload = jwt.decode(token, test_secret, algorithms=[ALGORITHM])

            assert "exp" in payload

    def test_expiry_uses_config_hours(self, test_user: User, test_secret: str):
        """Token expiry should be based on config jwt_expiry_hours."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 48

            before = datetime.now(timezone.utc)
            token = create_access_token(test_user)
            after = datetime.now(timezone.utc)

            payload = jwt.decode(token, test_secret, algorithms=[ALGORITHM])
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

            # Expiry should be ~48 hours from now (with 1 second tolerance for timing)
            expected_min = before + timedelta(hours=48) - timedelta(seconds=1)
            expected_max = after + timedelta(hours=48) + timedelta(seconds=1)

            assert expected_min <= exp <= expected_max


class TestDecodeToken:
    """Tests for decode_token function."""

    def test_decodes_valid_token(self, test_user: User, test_secret: str):
        """Should successfully decode a valid token."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(test_user)
            token_data = decode_token(token)

            assert token_data.email == test_user.email
            assert token_data.name == test_user.name
            assert token_data.picture == test_user.picture

    def test_raises_on_expired_token(self, test_user: User, test_secret: str):
        """Should raise TokenExpiredError for expired tokens."""
        # Create an already-expired token
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "email": test_user.email,
            "name": test_user.name,
            "picture": test_user.picture,
            "exp": expire,
        }
        expired_token = jwt.encode(payload, test_secret, algorithm=ALGORITHM)

        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret

            with pytest.raises(TokenExpiredError):
                decode_token(expired_token)

    def test_raises_on_invalid_signature(self, test_user: User, test_secret: str):
        """Should raise TokenInvalidError for wrong signature."""
        # Create token with different secret
        payload = {
            "email": test_user.email,
            "name": test_user.name,
            "picture": test_user.picture,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        wrong_secret_token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)

        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret

            with pytest.raises(TokenInvalidError):
                decode_token(wrong_secret_token)

    def test_raises_on_malformed_token(self, test_secret: str):
        """Should raise TokenInvalidError for malformed tokens."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret

            with pytest.raises(TokenInvalidError):
                decode_token("not-a-valid-jwt-token")

    def test_raises_on_empty_token(self, test_secret: str):
        """Should raise TokenInvalidError for empty token."""
        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret

            with pytest.raises(TokenInvalidError):
                decode_token("")


class TestUserWithoutPicture:
    """Tests for users without profile picture."""

    def test_handles_none_picture(self, test_secret: str):
        """Should handle user without picture."""
        user = User(
            email="nopic@example.com",
            name="No Picture",
            picture=None,
        )

        with patch("app.auth.jwt.settings") as mock_settings:
            mock_settings.jwt_secret = test_secret
            mock_settings.jwt_expiry_hours = 24

            token = create_access_token(user)
            token_data = decode_token(token)

            assert token_data.email == user.email
            assert token_data.picture is None
