"""
Tests for Goal CRUD operations.

Comprehensive test suite covering all goal endpoints, filtering, and edge cases.
"""

from datetime import datetime
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
    """Second test user email for ownership testing."""
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
def sample_goal_data():
    """Factory for creating sample goal data."""

    def _create(category="health", description="Exercise 3x per week"):
        return {
            "category": category,
            "description": description,
        }

    return _create


class TestCreateGoal:
    """Tests for POST /api/goals."""

    def test_create_goal_success(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should create new goal with valid data."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        goal_data = sample_goal_data()
        response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["category"] == goal_data["category"]
        assert data["description"] == goal_data["description"]
        assert "id" in data
        assert data["active"] is True
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_goal_requires_authentication(self, client, sample_goal_data):
        """Should return 401 without authentication."""
        goal_data = sample_goal_data()
        response = client.post("/api/goals", json=goal_data)

        assert response.status_code == 401


class TestGetGoals:
    """Tests for GET /api/goals."""

    def test_list_goals_success(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should list all goals."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # Create multiple goals
        make_authenticated_request(
            client, "test@example.com", "post", "/api/goals",
            json=sample_goal_data(category="health")
        )
        make_authenticated_request(
            client, "test@example.com", "post", "/api/goals",
            json=sample_goal_data(category="productivity")
        )

        response = make_authenticated_request(
            client, "test@example.com", "get", "/api/goals"
        )

        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        assert len(data["goals"]) == 2

    def test_list_goals_filter_by_active(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should filter goals by active status."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # Create active goal
        response1 = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals",
            json=sample_goal_data(category="health")
        )
        goal_id = response1.json()["id"]

        # Deactivate it
        make_authenticated_request(
            client, "test@example.com", "put", f"/api/goals/{goal_id}",
            json={"active": False}
        )

        # Create another active goal
        make_authenticated_request(
            client, "test@example.com", "post", "/api/goals",
            json=sample_goal_data(category="productivity")
        )

        # Filter by active=true
        response = make_authenticated_request(
            client, "test@example.com", "get", "/api/goals?active=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["active"] is True

    def test_list_goals_empty(
        self, client, test_db, test_user_id, monkeypatch
    ):
        """Should return empty list when no goals exist."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        response = make_authenticated_request(
            client, "test@example.com", "get", "/api/goals"
        )

        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        assert len(data["goals"]) == 0

    def test_list_goals_requires_authentication(self, client):
        """Should return 401 without authentication."""
        response = client.get("/api/goals")
        assert response.status_code == 401


class TestGetGoal:
    """Tests for GET /api/goals/{id}."""

    def test_get_goal_success(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should return goal by ID."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # Create goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # Get goal
        response = make_authenticated_request(
            client, "test@example.com", "get", f"/api/goals/{goal_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == goal_id
        assert data["category"] == goal_data["category"]

    def test_get_goal_not_found(self, client, test_db, test_user_id, monkeypatch):
        """Should return 404 for non-existent goal."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        fake_id = str(uuid4())
        response = make_authenticated_request(
            client, "test@example.com", "get", f"/api/goals/{fake_id}"
        )

        assert response.status_code == 404

    def test_get_goal_requires_authentication(self, client):
        """Should return 401 without authentication."""
        fake_id = str(uuid4())
        response = client.get(f"/api/goals/{fake_id}")
        assert response.status_code == 401


class TestUpdateGoal:
    """Tests for PUT /api/goals/{id}."""

    def test_update_goal_success(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should update goal fields."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # Create goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # Update goal
        update_data = {"description": "Updated description"}
        response = make_authenticated_request(
            client, "test@example.com", "put", f"/api/goals/{goal_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_goal_toggle_active(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should toggle active status."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # Create goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # Deactivate
        response = make_authenticated_request(
            client, "test@example.com", "put", f"/api/goals/{goal_id}",
            json={"active": False}
        )

        assert response.status_code == 200
        assert response.json()["active"] is False

    def test_update_goal_not_found(self, client, test_db, test_user_id, monkeypatch):
        """Should return 404 for non-existent goal."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        fake_id = str(uuid4())
        response = make_authenticated_request(
            client, "test@example.com", "put", f"/api/goals/{fake_id}",
            json={"description": "Updated"}
        )

        assert response.status_code == 404


class TestDeleteGoal:
    """Tests for DELETE /api/goals/{id}."""

    def test_delete_goal_soft_delete(
        self, client, test_db, test_user_id, sample_goal_data, monkeypatch
    ):
        """Should soft delete goal (set active=false)."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # Create goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # Delete goal
        response = make_authenticated_request(
            client, "test@example.com", "delete", f"/api/goals/{goal_id}"
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify goal still exists but is inactive
        get_response = make_authenticated_request(
            client, "test@example.com", "get", f"/api/goals/{goal_id}"
        )
        assert get_response.status_code == 200
        assert get_response.json()["active"] is False

    def test_delete_goal_not_found(self, client, test_db, test_user_id, monkeypatch):
        """Should return 404 for non-existent goal."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        fake_id = str(uuid4())
        response = make_authenticated_request(
            client, "test@example.com", "delete", f"/api/goals/{fake_id}"
        )

        assert response.status_code == 404


class TestGoalOwnership:
    """Tests for goal ownership validation - users cannot access each other's goals."""

    def test_cannot_get_other_user_goal(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_goal_data,
        monkeypatch,
    ):
        """User B should get 404 when trying to access User A's goal."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # User A creates goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # User B tries to get User A's goal - should get 404
        response = make_authenticated_request(
            client, "another@example.com", "get", f"/api/goals/{goal_id}"
        )
        assert response.status_code == 404

    def test_cannot_update_other_user_goal(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_goal_data,
        monkeypatch,
    ):
        """User B should not be able to update User A's goal."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # User A creates goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # User B tries to update User A's goal - should get 404
        response = make_authenticated_request(
            client,
            "another@example.com",
            "put",
            f"/api/goals/{goal_id}",
            json={"description": "Hacked content"},
        )
        assert response.status_code == 404

        # Verify goal was NOT updated by checking with User A
        verify_response = make_authenticated_request(
            client, "test@example.com", "get", f"/api/goals/{goal_id}"
        )
        assert verify_response.json()["description"] == goal_data["description"]

    def test_cannot_delete_other_user_goal(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_goal_data,
        monkeypatch,
    ):
        """User B should not be able to delete User A's goal."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # User A creates goal
        goal_data = sample_goal_data()
        create_response = make_authenticated_request(
            client, "test@example.com", "post", "/api/goals", json=goal_data
        )
        goal_id = create_response.json()["id"]

        # User B tries to delete User A's goal - should get 404
        response = make_authenticated_request(
            client, "another@example.com", "delete", f"/api/goals/{goal_id}"
        )
        assert response.status_code == 404

        # Verify goal still exists and is active for User A
        verify_response = make_authenticated_request(
            client, "test@example.com", "get", f"/api/goals/{goal_id}"
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["active"] is True

    def test_cannot_see_other_user_goals_in_list(
        self,
        client,
        test_db,
        test_user_id,
        second_user_id,
        sample_goal_data,
        monkeypatch,
    ):
        """Users should only see their own goals in list."""
        from contextlib import contextmanager

        @contextmanager
        def mock_get_db():
            yield test_db

        monkeypatch.setattr("app.routers.goals.get_db", mock_get_db)

        # User A creates goals
        make_authenticated_request(
            client, "test@example.com", "post", "/api/goals",
            json=sample_goal_data(category="health")
        )
        make_authenticated_request(
            client, "test@example.com", "post", "/api/goals",
            json=sample_goal_data(category="productivity")
        )

        # User B creates goal
        make_authenticated_request(
            client, "another@example.com", "post", "/api/goals",
            json=sample_goal_data(category="skills")
        )

        # User A should only see their 2 goals
        response_a = make_authenticated_request(
            client, "test@example.com", "get", "/api/goals"
        )
        assert response_a.status_code == 200
        assert len(response_a.json()["goals"]) == 2

        # User B should only see their 1 goal
        response_b = make_authenticated_request(
            client, "another@example.com", "get", "/api/goals"
        )
        assert response_b.status_code == 200
        assert len(response_b.json()["goals"]) == 1
