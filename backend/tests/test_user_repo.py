"""
Tests for User repository operations.

Comprehensive test suite covering user CRUD operations and race condition handling.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from app.database import get_connection, init_schema
from app.models.user import User, UserInDB
from app.repositories import user_repo


@pytest.fixture
def test_db(test_db_path):
    """Initialize test database with schema."""
    conn = get_connection(test_db_path)
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return User(
        email="test@example.com",
        name="Test User",
        picture="https://example.com/photo.jpg",
    )


class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    def test_get_existing_user(self, test_db, sample_user):
        """Should return user when found."""
        # Create user first
        created_user = user_repo.create_user(test_db, sample_user)

        # Retrieve user
        retrieved_user = user_repo.get_user_by_email(test_db, sample_user.email)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == sample_user.email
        assert retrieved_user.name == sample_user.name
        assert retrieved_user.picture == sample_user.picture
        assert isinstance(retrieved_user, UserInDB)

    def test_get_nonexistent_user(self, test_db):
        """Should return None when user not found."""
        result = user_repo.get_user_by_email(test_db, "nonexistent@example.com")
        assert result is None

    def test_email_case_insensitive_not_enforced(self, test_db, sample_user):
        """Email comparison is case-sensitive in database."""
        # Create user with lowercase email
        user_repo.create_user(test_db, sample_user)

        # Try to retrieve with uppercase - should not find (database is case-sensitive)
        result = user_repo.get_user_by_email(test_db, sample_user.email.upper())
        assert result is None


class TestCreateUser:
    """Tests for create_user function."""

    def test_create_user_success(self, test_db, sample_user):
        """Should create user with all fields."""
        created_user = user_repo.create_user(test_db, sample_user)

        assert created_user is not None
        assert isinstance(created_user, UserInDB)
        assert created_user.email == sample_user.email
        assert created_user.name == sample_user.name
        assert created_user.picture == sample_user.picture
        assert created_user.id is not None
        assert created_user.created_at is not None
        assert created_user.last_login_at is not None

    def test_create_user_persists_to_database(self, test_db, sample_user):
        """Should store user in database."""
        created_user = user_repo.create_user(test_db, sample_user)

        # Verify it's actually in the database
        result = test_db.execute(
            "SELECT id, email, name FROM users WHERE email = ?",
            [sample_user.email],
        ).fetchone()

        assert result is not None
        assert str(created_user.id) == str(result[0])
        assert result[1] == sample_user.email
        assert result[2] == sample_user.name

    def test_create_user_handles_race_condition(self, test_db, sample_user):
        """Should handle race condition when user already exists."""
        # Create user first time
        first_user = user_repo.create_user(test_db, sample_user)

        # Try to create again (simulates race condition)
        # Should return existing user instead of crashing
        second_user = user_repo.create_user(test_db, sample_user)

        # Should return the same user (by ID)
        assert second_user.id == first_user.id
        assert second_user.email == sample_user.email

    def test_create_user_without_picture(self, test_db):
        """Should handle user without picture."""
        user = User(
            email="nopicture@example.com",
            name="No Picture User",
            picture=None,
        )

        created_user = user_repo.create_user(test_db, user)

        assert created_user.email == user.email
        assert created_user.picture is None


class TestUpdateLastLogin:
    """Tests for update_last_login function."""

    def test_update_last_login_success(self, test_db, sample_user):
        """Should update last_login_at timestamp."""
        # Create user
        created_user = user_repo.create_user(test_db, sample_user)
        original_login = created_user.last_login_at

        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.1)

        # Update last login
        user_repo.update_last_login(test_db, created_user.id)

        # Retrieve and verify
        updated_user = user_repo.get_user_by_email(test_db, sample_user.email)
        assert updated_user.last_login_at > original_login

    def test_update_last_login_persists(self, test_db, sample_user):
        """Should persist last_login_at to database."""
        created_user = user_repo.create_user(test_db, sample_user)

        # Update last login
        user_repo.update_last_login(test_db, created_user.id)

        # Verify in database
        result = test_db.execute(
            "SELECT last_login_at FROM users WHERE id = ?",
            [str(created_user.id)],
        ).fetchone()

        assert result is not None
        assert result[0] is not None


class TestUserRepositoryIntegration:
    """Integration tests for user repository."""

    def test_full_user_lifecycle(self, test_db):
        """Test complete user create-retrieve-update flow."""
        # Create user
        user = User(
            email="lifecycle@example.com",
            name="Lifecycle Test",
            picture="https://example.com/pic.jpg",
        )

        created = user_repo.create_user(test_db, user)
        assert created.id is not None

        # Retrieve user
        retrieved = user_repo.get_user_by_email(test_db, user.email)
        assert retrieved.id == created.id

        # Update last login
        user_repo.update_last_login(test_db, retrieved.id)

        # Retrieve again and verify update
        final = user_repo.get_user_by_email(test_db, user.email)
        assert final.last_login_at >= created.last_login_at

    def test_multiple_users(self, test_db):
        """Should handle multiple users independently."""
        user1 = User(email="user1@example.com", name="User 1", picture=None)
        user2 = User(email="user2@example.com", name="User 2", picture=None)

        created1 = user_repo.create_user(test_db, user1)
        created2 = user_repo.create_user(test_db, user2)

        assert created1.id != created2.id
        assert created1.email != created2.email

        # Verify both can be retrieved
        retrieved1 = user_repo.get_user_by_email(test_db, user1.email)
        retrieved2 = user_repo.get_user_by_email(test_db, user2.email)

        assert retrieved1.id == created1.id
        assert retrieved2.id == created2.id


class TestRaceConditionHandling:
    """Specific tests for race condition scenarios."""

    def test_concurrent_creation_returns_same_user(self, test_db, sample_user):
        """Simulates concurrent creation - both should get same user."""
        # First create succeeds
        user1 = user_repo.create_user(test_db, sample_user)

        # Second create (race condition) should return existing
        user2 = user_repo.create_user(test_db, sample_user)

        # Both should reference the same database user
        assert user1.id == user2.id
        assert user1.email == user2.email
        assert user1.created_at == user2.created_at

    def test_create_after_failed_insert_returns_existing(self, test_db, sample_user):
        """After INSERT fails, should re-fetch and return existing user."""
        # Create user normally
        first_user = user_repo.create_user(test_db, sample_user)

        # Try to create again - will hit race condition path
        second_attempt = user_repo.create_user(test_db, sample_user)

        # Verify we got the existing user back
        assert second_attempt.id == first_user.id
        
        # Verify only one user exists in database
        result = test_db.execute(
            "SELECT COUNT(*) FROM users WHERE email = ?",
            [sample_user.email],
        ).fetchone()
        assert result[0] == 1
