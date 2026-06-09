"""Tests for the Google OAuth URL builder and the /api/auth login/logout flow."""

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.auth import oauth
from app.auth.dependencies import AUTH_COOKIE_NAME
from app.auth.oauth import GOOGLE_AUTH_URL, get_google_auth_url
from app.main import app
from app.models.user import User
from app.repositories import user_repo
from app.routers import auth as auth_router
from app.utils.timestamp import utc_now

from tests.conftest import make_mock_db


def _params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


# ── URL builder tests ──────────────────────────────────────────────────────


def test_url_points_at_google():
    url = get_google_auth_url()
    assert url.startswith(GOOGLE_AUTH_URL + "?")


def test_no_prompt_consent():
    """Regression: prompt=consent would force the consent screen on every login."""
    url = get_google_auth_url()
    params = _params(url)
    assert "prompt" not in params


def test_force_consent_adds_prompt():
    """Explicit ``force_consent=True`` adds ``prompt=consent`` so Google re-issues the refresh token."""
    url = get_google_auth_url(force_consent=True)
    params = _params(url)
    assert params.get("prompt") == ["consent"]


def test_access_type_offline_preserved():
    """access_type=offline is what makes Google issue the initial refresh_token."""
    url = get_google_auth_url()
    params = _params(url)
    assert params.get("access_type") == ["offline"]


def test_login_hint_included_when_allowed_email_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(oauth.settings, "allowed_email", "user@example.com")
    url = get_google_auth_url()
    params = _params(url)
    assert params.get("login_hint") == ["user@example.com"]


def test_login_hint_absent_when_allowed_email_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(oauth.settings, "allowed_email", "")
    url = get_google_auth_url()
    params = _params(url)
    assert "login_hint" not in params


def test_state_param_round_trips():
    url = get_google_auth_url(state="abc123")
    params = _params(url)
    assert params.get("state") == ["abc123"]


# ── /api/auth/login: self-healing prompt=consent ──────────────────────────


@pytest.fixture
def client(in_memory_db, monkeypatch: pytest.MonkeyPatch):
    """TestClient with auth.get_db patched to use the in-memory db."""
    monkeypatch.setattr(auth_router, "get_db", make_mock_db(in_memory_db))
    return TestClient(app)


def _seed_user(conn, email: str, refresh_token: str | None) -> None:
    """Create a user row, then optionally set its refresh_token."""
    user = user_repo.create_user(conn, User(email=email, name="Test"))
    if refresh_token is not None:
        user_repo.update_refresh_token(
            conn, user.id, refresh_token, utc_now() + timedelta(days=365)
        )


def test_login_no_consent_when_token_present(
    client, in_memory_db, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(auth_router.settings, "allowed_email", "user@example.com")
    _seed_user(in_memory_db, "user@example.com", "stored-refresh-token")

    resp = client.get("/api/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    params = _params(resp.headers["location"])
    assert "prompt" not in params


def test_login_forces_consent_when_refresh_token_null(
    client, in_memory_db, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(auth_router.settings, "allowed_email", "user@example.com")
    _seed_user(in_memory_db, "user@example.com", refresh_token=None)

    resp = client.get("/api/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    params = _params(resp.headers["location"])
    assert params.get("prompt") == ["consent"]


def test_login_forces_consent_when_user_missing(
    client, monkeypatch: pytest.MonkeyPatch
):
    """First-ever login: no row in DB yet → force consent so Google issues a refresh_token."""
    monkeypatch.setattr(auth_router.settings, "allowed_email", "user@example.com")

    resp = client.get("/api/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    params = _params(resp.headers["location"])
    assert params.get("prompt") == ["consent"]


def test_login_reconnect_param_forces_consent_even_with_token(
    client, in_memory_db, monkeypatch: pytest.MonkeyPatch
):
    """Manual recovery: ?reconnect=true forces consent regardless of DB state."""
    monkeypatch.setattr(auth_router.settings, "allowed_email", "user@example.com")
    _seed_user(in_memory_db, "user@example.com", "stored-refresh-token")

    resp = client.get("/api/auth/login?reconnect=true", follow_redirects=False)
    assert resp.status_code == 307
    params = _params(resp.headers["location"])
    assert params.get("prompt") == ["consent"]


# ── /api/auth/logout: must NOT clear refresh_token ─────────────────────────


def test_logout_does_not_clear_refresh_token(client, in_memory_db):
    _seed_user(in_memory_db, "user@example.com", "stored-refresh-token")

    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200

    # Auth cookie cleared
    set_cookie = resp.headers.get("set-cookie", "")
    assert AUTH_COOKIE_NAME in set_cookie

    # refresh_token preserved in DB
    user = user_repo.get_user_by_email(in_memory_db, "user@example.com")
    assert user is not None
    assert user.refresh_token == "stored-refresh-token"


def test_logout_works_without_cookie(client):
    """Logout is a no-auth operation — clearing a cookie needs no token."""
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert AUTH_COOKIE_NAME in resp.headers.get("set-cookie", "")
