"""Ingest endpoint tests."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.proposal import TaskProposal
from app.models.user import User

from tests.conftest import make_mock_db

_TEST_USER = User(email="test@example.com", name="Test User")

_SAMPLE_PROPOSALS = [
    TaskProposal(
        id="p1", source_id="s1", title="Buy groceries",
        source_type="notes", source_text="buy groceries", status="pending",
    ),
    TaskProposal(
        id="p2", source_id="s1", title="Call dentist",
        source_type="notes", source_text="call dentist", status="pending",
    ),
]


@pytest.fixture
def client(in_memory_db):
    """TestClient with auth + db overridden."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    import app.routers.ingest as ingest_mod
    ingest_mod.get_db = make_mock_db(in_memory_db)
    tc = TestClient(app)
    yield tc, in_memory_db
    app.dependency_overrides.clear()
    ingest_mod.get_db = __import__("app.database", fromlist=["get_db"]).get_db


# ── SSE path ──────────────────────────────────────────────────────────


def test_ingest_sse_creates_conversation(client):
    tc, db = client
    with patch("app.routers.ingest.TaskExtractor") as MockExtractor:
        MockExtractor.return_value.extract = AsyncMock(return_value=_SAMPLE_PROPOSALS)
        res = tc.post(
            "/api/ingest",
            json={"text": "buy groceries and call dentist"},
            headers={"Accept": "text/event-stream"},
        )

    assert res.status_code == 200

    # Parse SSE events
    events = _parse_sse(res.text)
    proposal_events = [e for e in events if e["event"] == "proposal"]
    done_events = [e for e in events if e["event"] == "done"]

    assert len(proposal_events) == 2
    assert len(done_events) == 1
    done_data = json.loads(done_events[0]["data"])
    assert "conversation_id" in done_data
    conv_id = done_data["conversation_id"]

    # Verify DB records
    conv = db.execute("SELECT * FROM conversations WHERE id = ?", [conv_id]).fetchone()
    assert conv is not None

    msgs = db.execute(
        "SELECT role, content, proposals_json FROM conversation_messages WHERE conversation_id = ? ORDER BY id",
        [conv_id],
    ).fetchall()
    assert len(msgs) == 2
    assert msgs[0][0] == "user"
    assert "groceries" in msgs[0][1]
    assert msgs[1][0] == "assistant"
    assert msgs[1][2] is not None  # proposals_json
    proposals = json.loads(msgs[1][2])
    assert len(proposals) == 2


# ── JSON path ─────────────────────────────────────────────────────────


def test_ingest_json_creates_conversation(client):
    tc, db = client
    with patch("app.routers.ingest.TaskExtractor") as MockExtractor:
        MockExtractor.return_value.extract = AsyncMock(return_value=_SAMPLE_PROPOSALS)
        res = tc.post(
            "/api/ingest",
            json={"text": "buy groceries and call dentist"},
        )

    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    conv_id = data["conversation_id"]

    conv = db.execute("SELECT * FROM conversations WHERE id = ?", [conv_id]).fetchone()
    assert conv is not None

    msgs = db.execute(
        "SELECT role FROM conversation_messages WHERE conversation_id = ?", [conv_id]
    ).fetchall()
    assert len(msgs) == 2


# ── No proposals → no conversation ────────────────────────────────────


def test_ingest_no_proposals_no_conversation(client):
    tc, db = client
    with patch("app.routers.ingest.TaskExtractor") as MockExtractor:
        MockExtractor.return_value.extract = AsyncMock(return_value=[])
        res = tc.post(
            "/api/ingest",
            json={"text": "nothing useful here"},
        )

    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" not in data

    count = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    assert count == 0


# ── Empty text → 400 ──────────────────────────────────────────────────


def test_ingest_empty_text(client):
    tc, _ = client
    res = tc.post("/api/ingest", json={"text": "   "})
    assert res.status_code == 400


# ── Helpers ───────────────────────────────────────────────────────────


def _parse_sse(raw: str) -> list[dict]:
    """Parse raw SSE text into list of {event, data} dicts."""
    events = []
    current_event = ""
    for line in raw.split("\n"):
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            events.append({"event": current_event, "data": line[5:].strip()})
            current_event = ""
    return events
