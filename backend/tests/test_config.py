"""Config endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User

from tests.conftest import make_mock_db

_TEST_USER = User(email="test@example.com", name="Test User")


@pytest.fixture
def client(in_memory_db):
    """TestClient with auth + db overridden."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    import app.routers.config as config_mod
    config_mod.get_db = make_mock_db(in_memory_db)
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()
    config_mod.get_db = __import__("app.database", fromlist=["get_db"]).get_db


def test_get_config_defaults(client):
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["ollama_model"] == "qwen3:4b"
    assert data["system_prompt_override"] is None


def test_update_config(client):
    res = client.put("/api/config", json={"system_prompt_override": "Always respond in Spanish"})
    assert res.status_code == 200
    data = res.json()
    assert data["system_prompt_override"] == "Always respond in Spanish"


def test_update_config_persists(client):
    client.put("/api/config", json={"system_prompt_override": "Be concise"})
    res = client.get("/api/config")
    assert res.json()["system_prompt_override"] == "Be concise"


def test_update_config_partial(client):
    """PUT only updates provided fields, leaves others unchanged."""
    client.put("/api/config", json={"system_prompt_override": "Custom prompt"})
    client.put("/api/config", json={"default_project_id": 42})
    res = client.get("/api/config")
    data = res.json()
    assert data["system_prompt_override"] == "Custom prompt"
    assert data["default_project_id"] == 42


def test_update_config_clear_override(client):
    """Setting system_prompt_override to None clears it."""
    client.put("/api/config", json={"system_prompt_override": "Something"})
    client.put("/api/config", json={"system_prompt_override": None})
    res = client.get("/api/config")
    assert res.json()["system_prompt_override"] is None


def test_get_system_prompt(client):
    """GET /api/config/system-prompt returns the formatted prompt."""
    res = client.get("/api/config/system-prompt")
    assert res.status_code == 200
    data = res.json()
    assert "prompt" in data
    assert isinstance(data["prompt"], str)
    assert len(data["prompt"]) > 0


def test_get_tools(client):
    """GET /api/config/tools returns a list of tools."""
    res = client.get("/api/config/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)
    assert len(data["tools"]) > 0


def test_update_base_prompt_override(client):
    """Set base_prompt_override, verify it persists."""
    res = client.put("/api/config", json={"base_prompt_override": "Custom base prompt for {today}"})
    assert res.status_code == 200
    assert res.json()["base_prompt_override"] == "Custom base prompt for {today}"

    # Verify it persists on subsequent GET
    res = client.get("/api/config")
    assert res.json()["base_prompt_override"] == "Custom base prompt for {today}"


def test_get_system_prompt_with_base_override(client):
    """GET /api/config/system-prompt uses base_prompt_override when set."""
    from datetime import date

    custom_base = "You are a custom assistant. Today is {today}."
    client.put("/api/config", json={"base_prompt_override": custom_base})

    res = client.get("/api/config/system-prompt")
    assert res.status_code == 200
    data = res.json()
    expected = f"You are a custom assistant. Today is {date.today().isoformat()}."
    assert data["prompt"] == expected


def test_get_config_includes_notification_fields(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notif_digest_enabled"] is True
    assert data["notif_digest_time"] == "08:00"
    assert data["notif_review_time"] == "21:00"
    assert data["notif_max_per_day"] == 5
    assert data["notif_max_nudges_per_day"] == 2
    assert data["notif_reminder_lead_hours"] == 2
    assert data["notif_quiet_start"] == 22
    assert data["notif_quiet_end"] == 7
    assert data["notif_nudge_runs_per_day"] == 3
    assert data["notif_timezone"] == "UTC"


def test_update_notification_fields(client):
    resp = client.put(
        "/api/config",
        json={"notif_digest_time": "07:30", "notif_nudges_enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notif_digest_time"] == "07:30"
    assert data["notif_nudges_enabled"] is False
    # untouched field keeps default
    assert data["notif_review_enabled"] is True


def test_update_rejects_invalid_notification_values(client):
    for payload in (
        {"notif_digest_time": "banana"},
        {"notif_digest_time": "25:00"},
        {"notif_quiet_start": 99},
        {"notif_reminder_lead_hours": -1},
        {"notif_timezone": "Mars/Olympus_Mons"},
    ):
        resp = client.put("/api/config", json=payload)
        assert resp.status_code == 422, payload


def test_zero_values_round_trip(client):
    resp = client.put(
        "/api/config",
        json={"notif_max_per_day": 0, "notif_max_nudges_per_day": 0, "notif_reminder_lead_hours": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notif_max_per_day"] == 0
    assert data["notif_max_nudges_per_day"] == 0
    assert data["notif_reminder_lead_hours"] == 0
