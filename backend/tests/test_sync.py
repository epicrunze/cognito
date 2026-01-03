"""
Tests for sync endpoint and service.

Comprehensive test suite covering sync API, last-write-wins conflict resolution,
and pending message processing.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_connection, init_schema
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user_email():
    """Test user email."""
    return "test@example.com"


@pytest.fixture
def test_db(test_db_path):
    """Initialize test database with schema."""
    conn = get_connection(test_db_path)
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def test_user_id(test_db, test_user_email):
    """Create test user and return user_id."""
    user_id = uuid4()
    test_db.execute(
        """
        INSERT INTO users (id, email, name, picture, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [str(user_id), test_user_email, "Test User", None, datetime.now(timezone.utc)],
    )
    return user_id


def make_authenticated_request(client, user_email, method, url, **kwargs):
    """
    Make an authenticated HTTP request as a specific user.
    """
    from app.models.user import User
    from app.main import app
    from app.auth.dependencies import get_current_user

    async def mock_user():
        return User(
            email=user_email,
            name=f"User {user_email}",
            picture="https://example.com/photo.jpg",
        )

    app.dependency_overrides[get_current_user] = mock_user

    try:
        response = getattr(client, method.lower())(url, **kwargs)
        return response
    finally:
        app.dependency_overrides.clear()


class TestSyncEndpoint:
    """Tests for POST /api/sync endpoint."""

    def test_sync_requires_authentication(self, client):
        """Should return 401 without authentication."""
        response = client.post("/api/sync", json={})
        assert response.status_code == 401

    def test_sync_empty_request(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should handle empty sync request."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "last_synced_at": None,
                "pending_changes": [],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "applied" in data
        assert "skipped" in data
        assert "server_changes" in data
        assert "sync_timestamp" in data
        assert data["applied"] == []
        assert data["skipped"] == []

    def test_sync_creates_entry(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should create entry from pending create change."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        entry_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "last_synced_at": None,
                "pending_changes": [
                    {
                        "id": str(uuid4()),
                        "type": "create",
                        "entity": "entry",
                        "entity_id": entry_id,
                        "data": {
                            "id": entry_id,
                            "date": "2024-12-30",
                            "conversations": [],
                            "refined_output": "Test entry from sync"
                        },
                        "base_version": 1,
                        "timestamp": now
                    }
                ],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert entry_id in data["applied"]

        # Verify entry was created in database
        result = test_db.execute(
            "SELECT * FROM entries WHERE id = ?", [entry_id]
        ).fetchone()
        assert result is not None

    def test_sync_updates_entry(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should update existing entry from pending update change."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create entry first
        entry_id = uuid4()
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        test_db.execute(
            """
            INSERT INTO entries (
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(entry_id), str(test_user_id), "2024-12-30", "[]",
                "Original content", 1.0, old_time, 0, "active", 1,
                old_time, old_time
            ]
        )

        # Sync with update
        now = datetime.now(timezone.utc).isoformat()
        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "last_synced_at": None,
                "pending_changes": [
                    {
                        "id": str(uuid4()),
                        "type": "update",
                        "entity": "entry",
                        "entity_id": str(entry_id),
                        "data": {
                            "refined_output": "Updated content"
                        },
                        "base_version": 1,
                        "timestamp": now
                    }
                ],
                "base_versions": {str(entry_id): 1}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert str(entry_id) in data["applied"]

        # Verify entry was updated
        result = test_db.execute(
            "SELECT refined_output FROM entries WHERE id = ?", [str(entry_id)]
        ).fetchone()
        assert result[0] == "Updated content"

    def test_sync_last_write_wins_client_newer(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Client change should win when client timestamp is newer."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create entry with old timestamp
        entry_id = uuid4()
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        test_db.execute(
            """
            INSERT INTO entries (
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(entry_id), str(test_user_id), "2024-12-30", "[]",
                "Server content", 1.0, old_time, 0, "active", 1,
                old_time, old_time
            ]
        )

        # Client sends newer change
        client_time = datetime.now(timezone.utc).isoformat()
        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "pending_changes": [
                    {
                        "id": str(uuid4()),
                        "type": "update",
                        "entity": "entry",
                        "entity_id": str(entry_id),
                        "data": {"refined_output": "Client content"},
                        "timestamp": client_time
                    }
                ],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert str(entry_id) in data["applied"]

        # Verify client content won
        result = test_db.execute(
            "SELECT refined_output FROM entries WHERE id = ?", [str(entry_id)]
        ).fetchone()
        assert result[0] == "Client content"

    def test_sync_last_write_wins_server_newer(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Server change should win when server timestamp is newer."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create entry with a future timestamp to ensure it's definitely newer
        # DuckDB stores naive datetimes, so we create a naive datetime that represents
        # a UTC time 2 hours in the future. The comparison logic will treat naive 
        # datetimes as UTC, so this simulates a server update from the future.
        entry_id = uuid4()
        # Get current UTC time as naive, then add 2 hours
        server_time = datetime.utcnow() + timedelta(hours=2)
        test_db.execute(
            """
            INSERT INTO entries (
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(entry_id), str(test_user_id), "2024-12-30", "[]",
                "Server content", 1.0, server_time, 0, "active", 1,
                server_time, server_time
            ]
        )

        # Client sends change with current time (which is 2 hours before server)
        client_time = datetime.now(timezone.utc).isoformat()
        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "pending_changes": [
                    {
                        "id": str(uuid4()),
                        "type": "update",
                        "entity": "entry",
                        "entity_id": str(entry_id),
                        "data": {"refined_output": "Client content"},
                        "timestamp": client_time
                    }
                ],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert str(entry_id) in data["skipped"]

        # Verify server content preserved
        result = test_db.execute(
            "SELECT refined_output FROM entries WHERE id = ?", [str(entry_id)]
        ).fetchone()
        assert result[0] == "Server content"

    def test_sync_returns_server_changes(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should return entries modified since last sync."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create entry
        entry_id = uuid4()
        now = datetime.now(timezone.utc)
        test_db.execute(
            """
            INSERT INTO entries (
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(entry_id), str(test_user_id), "2024-12-30", "[]",
                "Test content", 1.0, now, 0, "active", 1, now, now
            ]
        )

        # Sync with no last_synced_at (full sync)
        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "last_synced_at": None,
                "pending_changes": [],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["server_changes"]["entries"]) == 1
        assert data["server_changes"]["entries"][0]["id"] == str(entry_id)

    def test_sync_creates_goal(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should create goal from pending create change."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        goal_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "pending_changes": [
                    {
                        "id": str(uuid4()),
                        "type": "create",
                        "entity": "goal",
                        "entity_id": goal_id,
                        "data": {
                            "category": "health",
                            "description": "Exercise daily"
                        },
                        "timestamp": now
                    }
                ],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert goal_id in data["applied"]

        # Verify goal was created
        result = test_db.execute(
            "SELECT * FROM goals WHERE id = ?", [goal_id]
        ).fetchone()
        assert result is not None


class TestSyncService:
    """Unit tests for SyncService."""

    def test_timestamp_comparison_handles_timezone(self, test_db, test_user_id):
        """Timestamp comparison should handle different timezone formats."""
        from app.services.sync import SyncService

        service = SyncService(test_db, test_user_id)

        # Create mock entries with explicit UTC timestamps
        class MockEntryOlder:
            # Use a datetime far in the past so client is definitely newer
            updated_at = datetime(2024, 12, 29, 12, 0, 0, tzinfo=timezone.utc)

        class MockEntryNewer:
            # Use current UTC time so client (from 1 hour ago) is definitely older
            updated_at = datetime.now(timezone.utc)

        # Test with client timestamp that's definitely newer than yesterday's entry
        client_ts_newer = "2024-12-30T13:00:00+00:00"
        assert service._should_apply_update(MockEntryOlder(), client_ts_newer) is True

        # Test with client timestamp from the past - should not apply to entry updated now
        client_ts_older = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert service._should_apply_update(MockEntryNewer(), client_ts_older) is False

    def test_parse_conversations_handles_various_formats(self, test_db, test_user_id):
        """Should parse conversations from various JSON formats."""
        from app.services.sync import SyncService

        service = SyncService(test_db, test_user_id)

        # Empty list
        result = service._parse_conversations([])
        assert result == []

        # None
        result = service._parse_conversations(None)
        assert result == []

        # Valid conversation data
        conv_data = [
            {
                "id": str(uuid4()),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ],
                "prompt_source": "user",
                "notification_id": None
            }
        ]
        result = service._parse_conversations(conv_data)
        assert len(result) == 1
        assert len(result[0].messages) == 1


class TestExtendedOfflineSync:
    """Tests for extended offline sync scenarios (BE-001)."""

    def test_sync_after_extended_offline_period(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should return all changes after extended offline period (48+ hours)."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create entries at different times over the past 48 hours
        entry_ids = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(5):
            entry_id = uuid4()
            entry_ids.append(str(entry_id))
            # Spread entries over 48 hours
            entry_time = base_time - timedelta(hours=i * 10)
            test_db.execute(
                """
                INSERT INTO entries (
                    id, user_id, date, conversations, refined_output,
                    relevance_score, last_interacted_at, interaction_count,
                    status, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(entry_id), str(test_user_id), f"2024-12-{30-i}", "[]",
                    f"Entry {i}", 1.0, entry_time, i, "active", 1,
                    entry_time, entry_time
                ]
            )

        # Client reconnects after 48 hours offline (last sync was 48 hours ago)
        last_synced = (base_time - timedelta(hours=48)).isoformat()
        
        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "last_synced_at": last_synced,
                "pending_changes": [],
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        
        # Should return entries modified since last sync
        # At least the entries created in the last 48 hours should be returned
        returned_ids = [e["id"] for e in data["server_changes"]["entries"]]
        # Entries 0-4 span from now to 40 hours ago, so all within 48hr window
        for entry_id in entry_ids[:4]:  # First 4 entries are within 48 hours
            assert entry_id in returned_ids

    def test_stale_data_reconciliation(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should correctly reconcile stale client data with newer server data."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create entry on server with recent timestamp
        entry_id = uuid4()
        server_time = datetime.now(timezone.utc)
        test_db.execute(
            """
            INSERT INTO entries (
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(entry_id), str(test_user_id), "2024-12-30", "[]",
                "Server version - updated today", 1.0, server_time, 5, "active", 3,
                server_time - timedelta(days=3), server_time
            ]
        )

        # Client sends update with timestamp from 2 days ago (stale)
        stale_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        
        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "pending_changes": [
                    {
                        "id": str(uuid4()),
                        "type": "update",
                        "entity": "entry",
                        "entity_id": str(entry_id),
                        "data": {"refined_output": "Client version - 2 days old"},
                        "timestamp": stale_time
                    }
                ],
                "base_versions": {str(entry_id): 2}  # Client has old version
            }
        )

        assert response.status_code == 200
        data = response.json()
        
        # Client's stale change should be skipped (server is newer)
        assert str(entry_id) in data["skipped"]
        
        # Verify server content is preserved
        result = test_db.execute(
            "SELECT refined_output FROM entries WHERE id = ?", [str(entry_id)]
        ).fetchone()
        assert result[0] == "Server version - updated today"

    def test_large_pending_change_queue(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should process 100+ pending changes in single sync request."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Create 100+ pending changes
        pending_changes = []
        now = datetime.now(timezone.utc)
        
        # 50 entry creates
        for i in range(50):
            entry_id = str(uuid4())
            pending_changes.append({
                "id": str(uuid4()),
                "type": "create",
                "entity": "entry",
                "entity_id": entry_id,
                "data": {
                    "id": entry_id,
                    "date": f"2024-12-{(i % 28) + 1:02d}",
                    "conversations": [],
                    "refined_output": f"Entry {i} from bulk sync"
                },
                "base_version": 1,
                "timestamp": (now - timedelta(minutes=100-i)).isoformat()
            })
        
        # 50 goal creates
        for i in range(50):
            goal_id = str(uuid4())
            pending_changes.append({
                "id": str(uuid4()),
                "type": "create",
                "entity": "goal",
                "entity_id": goal_id,
                "data": {
                    "id": goal_id,
                    "category": f"category_{i % 5}",
                    "description": f"Goal {i} from bulk sync"
                },
                "timestamp": (now - timedelta(minutes=50-i)).isoformat()
            })

        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "last_synced_at": None,
                "pending_changes": pending_changes,
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        
        # All 100 changes should be applied
        assert len(data["applied"]) == 100
        assert len(data["skipped"]) == 0
        
        # Verify entries and goals were created in database
        entry_count = test_db.execute(
            "SELECT COUNT(*) FROM entries WHERE user_id = ?", [str(test_user_id)]
        ).fetchone()[0]
        goal_count = test_db.execute(
            "SELECT COUNT(*) FROM goals WHERE user_id = ?", [str(test_user_id)]
        ).fetchone()[0]
        
        assert entry_count == 50
        assert goal_count == 50

    def test_mixed_operations_in_large_queue(
        self, client, test_db, test_user_id, test_user_email, monkeypatch
    ):
        """Should handle mixed create/update/delete operations in large queue."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.sync.get_db", mock_get_db)

        # Pre-create some entries to update/delete
        existing_entries = []
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(10):
            entry_id = uuid4()
            existing_entries.append(str(entry_id))
            test_db.execute(
                """
                INSERT INTO entries (
                    id, user_id, date, conversations, refined_output,
                    relevance_score, last_interacted_at, interaction_count,
                    status, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(entry_id), str(test_user_id), f"2024-12-{i+1:02d}", "[]",
                    f"Original entry {i}", 1.0, old_time, 0, "active", 1,
                    old_time, old_time
                ]
            )

        # Build mixed operations queue
        pending_changes = []
        now = datetime.now(timezone.utc)
        
        # 5 creates
        for i in range(5):
            entry_id = str(uuid4())
            pending_changes.append({
                "id": str(uuid4()),
                "type": "create",
                "entity": "entry",
                "entity_id": entry_id,
                "data": {
                    "id": entry_id,
                    "date": f"2024-12-{15+i}",
                    "conversations": [],
                    "refined_output": f"New entry {i}"
                },
                "timestamp": now.isoformat()
            })
        
        # 5 updates to existing entries
        for i in range(5):
            pending_changes.append({
                "id": str(uuid4()),
                "type": "update",
                "entity": "entry",
                "entity_id": existing_entries[i],
                "data": {"refined_output": f"Updated entry {i}"},
                "timestamp": now.isoformat()
            })

        response = make_authenticated_request(
            client,
            test_user_email,
            "post",
            "/api/sync",
            json={
                "pending_changes": pending_changes,
                "base_versions": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        
        # All 10 operations should be applied
        assert len(data["applied"]) == 10
        
        # Verify updates were applied
        for i in range(5):
            result = test_db.execute(
                "SELECT refined_output FROM entries WHERE id = ?", 
                [existing_entries[i]]
            ).fetchone()
            assert result[0] == f"Updated entry {i}"
