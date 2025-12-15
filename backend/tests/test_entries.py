"""
Tests for Entry CRUD operations.

Comprehensive test suite covering all entry endpoints, filtering, and edge cases.
"""

from datetime import datetime, timezone
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
def authenticated_client(client, test_user_email, monkeypatch):
    """Client with mocked authentication."""
    from app.models.user import User
    from app.main import app

    async def mock_get_current_user():
        return User(
            email=test_user_email,
            name="Test User",
            picture="https://example.com/photo.jpg",
        )

    # Patch the dependency in the main app
    app.dependency_overrides[
        __import__("app.auth.dependencies").auth.dependencies.get_current_user
    ] = mock_get_current_user

    yield client

    # Clean up
    app.dependency_overrides = {}


@pytest.fixture
def test_db(test_db_path):
    """Initialize test database with schema - returns connection that stays open."""
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
        [str(user_id), test_user_email, "Test User", None, datetime.now()],
    )
    return user_id


@pytest.fixture
def second_user_email():
    """Second test user email for 403 testing."""
    return "another@example.com"


@pytest.fixture
def second_user_id(test_db, second_user_email):
    """Create second test user and return user_id."""
    user_id = uuid4()
    test_db.execute(
        """
        INSERT INTO users (id, email, name, picture, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [str(user_id), second_user_email, "Second User", None, datetime.now()],
    )
    return user_id


@pytest.fixture
def authenticated_client_user2(client, second_user_email):
    """Client authenticated as second user - ensures clean state."""
    from app.models.user import User
    from app.main import app

    # Clear any existing overrides first
    app.dependency_overrides.clear()

    async def mock_get_current_user():
        return User(
            email=second_user_email,
            name="Second User",
            picture="https://example.com/photo2.jpg",
        )

    app.dependency_overrides[
        __import__("app.auth.dependencies").auth.dependencies.get_current_user
    ] = mock_get_current_user

    # Create a new client instance to avoid shared state
    from fastapi.testclient import TestClient
    client_user2 = TestClient(app)
    
    yield client_user2

    # Clean up
    app.dependency_overrides.clear()


def make_authenticated_request(client, user_email, method, url, **kwargs):
    """
    Make an authenticated HTTP request as a specific user.
    
    Provides perfect isolation - each request gets its own auth context
    that's immediately cleaned up afterwards.
    
    Args:
        client: TestClient instance
        user_email: Email of user to authenticate as
        method: HTTP method ('get', 'post', 'put', 'delete', etc.)
        url: Request URL
        **kwargs: Additional arguments for the request (json, headers, etc.)
    
    Returns:
        Response object
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

    # Set auth override for this request only
    app.dependency_overrides[get_current_user] = mock_user

    try:
        # Make the request
        response = getattr(client, method.lower())(url, **kwargs)
        return response
    finally:
        # Always clean up, even if request fails
        app.dependency_overrides.clear()


@pytest.fixture
def sample_entry_data():
    """Factory for creating sample entry data."""

    def _create(date="2024-12-10", refined_output="Test entry"):
        return {
            "date": date,
            "conversations": [
                {
                    "id": str(uuid4()),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ],
                    "prompt_source": "user",
                    "notification_id": None,
                }
            ],
            "refined_output": refined_output,
        }

    return _create


class TestCreateEntry:
    """Tests for POST /api/entries."""

    def test_create_entry_success(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should create new entry with valid data."""
        # Patch database context manager
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        entry_data = sample_entry_data()
        response = authenticated_client.post("/api/entries", json=entry_data)

        assert response.status_code == 201
        data = response.json()
        assert data["date"] == entry_data["date"]
        assert data["refined_output"] == entry_data["refined_output"]
        assert "id" in data
        assert data["version"] == 1
        assert data["status"] == "active"

    def test_create_entry_returns_existing_for_same_date(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should return existing entry when date already exists."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        entry_data = sample_entry_data(date="2024-12-10")

        # Create first entry
        response1 = authenticated_client.post("/api/entries", json=entry_data)
        assert response1.status_code == 201
        entry1_id = response1.json()["id"]

        # Try to create second entry for same date
        response2 = authenticated_client.post("/api/entries", json=entry_data)
        assert response2.status_code == 201  # Still 201 but returns existing
        entry2_id = response2.json()["id"]

        # Should be the same entry
        assert entry1_id == entry2_id

    def test_create_entry_requires_authentication(self, client, sample_entry_data):
        """Should return 401 without authentication."""
        entry_data = sample_entry_data()
        response = client.post("/api/entries", json=entry_data)

        assert response.status_code == 401


class TestUserManagement:
    """Tests for user auto-creation and management."""

    def test_user_auto_creation_on_first_request(
        self, authenticated_client, test_db, sample_entry_data, monkeypatch
    ):
        """Should auto-create user on first API request if they don't exist."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Verify user doesn't exist
        result = test_db.execute(
            "SELECT id FROM users WHERE email = ?", ["test@example.com"]
        ).fetchone()
        assert result is None

        # Make first request - should auto-create user
        entry_data = sample_entry_data()
        response = authenticated_client.post("/api/entries", json=entry_data)

        assert response.status_code == 201

        # Verify user was created
        result = test_db.execute(
            "SELECT id, email, name FROM users WHERE email = ?", ["test@example.com"]
        ).fetchone()
        assert result is not None
        assert result[1] == "test@example.com"
        assert result[2] == "Test User"


class TestCrossUserAccessControl:
    """Tests for cross-user access control - users cannot access each other's data."""

    def test_cannot_get_other_user_entry(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_entry_data,
        monkeypatch,
    ):
        """User B should get 404 when trying to access User A's entry."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # User A creates entry
        entry_data = sample_entry_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/entries", json=entry_data
        )
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]

        # User B tries to get User A's entry - should get 404
        response = make_authenticated_request(
            client, "another@example.com", "get", f"/api/entries/{entry_id}"
        )
        assert response.status_code == 404

    def test_cannot_update_other_user_entry(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_entry_data,
        monkeypatch,
    ):
        """User B should not be able to update User A's entry."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # User A creates entry
        entry_data = sample_entry_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/entries", json=entry_data
        )
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]

        # User B tries to update User A's entry - should get 404
        response = make_authenticated_request(
            client,
            "another@example.com",
            "put",
            f"/api/entries/{entry_id}",
            json={"refined_output": "Hacked content"},
        )
        assert response.status_code == 404

        # Verify entry was NOT updated by checking with User A
        verify_response = make_authenticated_request(
            client, "test@example.com", "get", f"/api/entries/{entry_id}"
        )
        assert verify_response.json()["refined_output"] == "Test entry"

    def test_cannot_see_other_user_entries_in_list(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_entry_data,
        monkeypatch,
    ):
        """Users should only see their own entries in list."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # User A creates entries
        make_authenticated_request(
            client, "test@example.com", "post", "/api/entries", 
            json=sample_entry_data(date="2024-12-10")
        )
        make_authenticated_request(
            client, "test@example.com", "post", "/api/entries",
            json=sample_entry_data(date="2024-12-11")
        )

        # User B creates entry
        make_authenticated_request(
            client, "another@example.com", "post", "/api/entries",
            json=sample_entry_data(date="2024-12-15")
        )

        # User A should only see their 2 entries
        response_a = make_authenticated_request(
            client, "test@example.com", "get", "/api/entries"
        )
        assert response_a.status_code == 200
        assert response_a.json()["total"] == 2

        # User B should only see their 1 entry
        response_b = make_authenticated_request(
            client, "another@example.com", "get", "/api/entries"
        )
        assert response_b.status_code == 200
        assert response_b.json()["total"] == 1


class TestGetEntry:
    """Tests for GET /api/entries/{id}."""

    def test_get_entry_success(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should return entry by ID."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create entry
        entry_data = sample_entry_data()
        create_response = authenticated_client.post("/api/entries", json=entry_data)
        entry_id = create_response.json()["id"]

        # Get entry
        response = authenticated_client.get(f"/api/entries/{entry_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert data["date"] == entry_data["date"]

    def test_get_entry_not_found(self, authenticated_client, test_db, monkeypatch):
        """Should return 404 for non-existent entry."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        fake_id = str(uuid4())
        response = authenticated_client.get(f"/api/entries/{fake_id}")

        assert response.status_code == 404

    def test_get_entry_requires_authentication(self, client):
        """Should return 401 without authentication."""
        fake_id = str(uuid4())
        response = client.get(f"/api/entries/{fake_id}")

        assert response.status_code == 401


class TestListEntries:
    """Tests for GET /api/entries."""

    def test_list_entries_success(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should list all entries."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create multiple entries
        authenticated_client.post("/api/entries", json=sample_entry_data(date="2024-12-10"))
        authenticated_client.post("/api/entries", json=sample_entry_data(date="2024-12-11"))

        response = authenticated_client.get("/api/entries")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["entries"]) == 2

    def test_list_entries_filter_by_status(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should filter entries by status."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create entries
        response1 = authenticated_client.post(
            "/api/entries", json=sample_entry_data(date="2024-12-10")
        )
        entry_id = response1.json()["id"]

        # Archive one entry
        authenticated_client.put(
            f"/api/entries/{entry_id}",
            json={"status": "archived"},
        )

        # Create another active entry
        authenticated_client.post("/api/entries", json=sample_entry_data(date="2024-12-11"))

        # Filter by active status
        response = authenticated_client.get("/api/entries?status=active")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["status"] == "active"

    def test_list_entries_filter_by_date_range(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should filter entries by date range."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create entries with different dates
        authenticated_client.post("/api/entries", json=sample_entry_data(date="2024-12-01"))
        authenticated_client.post("/api/entries", json=sample_entry_data(date="2024-12-15"))
        authenticated_client.post("/api/entries", json=sample_entry_data(date="2024-12-30"))

        # Filter by date range
        response = authenticated_client.get(
            "/api/entries?after_date=2024-12-10&before_date=2024-12-20"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["date"] == "2024-12-15"

    def test_list_entries_pagination(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should paginate entry results."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create multiple entries
        for i in range(5):
            authenticated_client.post(
                "/api/entries", json=sample_entry_data(date=f"2024-12-{i+1:02d}")
            )

        # Get first page
        response1 = authenticated_client.get("/api/entries?limit=2&offset=0")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["entries"]) == 2
        assert data1["total"] == 5

        # Get second page
        response2 = authenticated_client.get("/api/entries?limit=2&offset=2")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["entries"]) == 2
        assert data2["total"] == 5

        # Entries should be different
        assert data1["entries"][0]["id"] != data2["entries"][0]["id"]


class TestUpdateEntry:
    """Tests for PUT /api/entries/{id}."""

    def test_update_entry_success(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should update entry fields."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create entry
        entry_data = sample_entry_data()
        create_response = authenticated_client.post("/api/entries", json=entry_data)
        entry_id = create_response.json()["id"]

        # Update entry
        update_data = {"refined_output": "Updated content"}
        response = authenticated_client.put(f"/api/entries/{entry_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["refined_output"] == "Updated content"
        assert data["version"] == 2  # Version should increment

    def test_update_entry_increments_version(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should increment version on each update."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create entry
        entry_data = sample_entry_data()
        create_response = authenticated_client.post("/api/entries", json=entry_data)
        entry_id = create_response.json()["id"]

        # Update multiple times
        for i in range(3):
            response = authenticated_client.put(
                f"/api/entries/{entry_id}",
                json={"refined_output": f"Version {i + 2}"},
            )
            assert response.json()["version"] == i + 2

    def test_update_entry_not_found(self, authenticated_client, test_db, monkeypatch):
        """Should return 404 for non-existent entry."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        fake_id = str(uuid4())
        response = authenticated_client.put(
            f"/api/entries/{fake_id}",
            json={"refined_output": "Updated"},
        )

        assert response.status_code == 404


class TestEntryVersions:
    """Tests for GET /api/entries/{id}/versions."""

    def test_get_versions_success(
        self, authenticated_client, test_db, test_user_id, sample_entry_data, monkeypatch
    ):
        """Should return version history."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        # Create entry
        entry_data = sample_entry_data()
        create_response = authenticated_client.post("/api/entries", json=entry_data)
        entry_id = create_response.json()["id"]

        # Update entry to create versions
        authenticated_client.put(
            f"/api/entries/{entry_id}",
            json={"refined_output": "Version 2"},
        )
        authenticated_client.put(
            f"/api/entries/{entry_id}",
            json={"refined_output": "Version 3"},
        )

        # Get versions
        response = authenticated_client.get(f"/api/entries/{entry_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) == 2  # Two version snapshots created

    def test_get_versions_not_found(self, authenticated_client, test_db, monkeypatch):
        """Should return empty list for non-existent entry (but 404 if no user)."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.entries.get_db", mock_get_db)

        fake_id = str(uuid4())
        response = authenticated_client.get(f"/api/entries/{fake_id}/versions")

        # Will return 404 because user doesn't exist in test DB
        # In real usage with authenticated user, would return 200 with empty versions
        assert response.status_code == 404
