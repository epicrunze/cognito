"""
Tests for Entry version snapshots and history.

Tests version creation, integrity, and retrieval.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_connection, init_schema
from app.main import app
from app.repositories import entry_repo
from app.models.entry import EntryCreate, Conversation, Message


@pytest.fixture
def test_db(test_db_path):
    """Initialize test database with schema."""
    conn = get_connection(test_db_path)
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def test_user_id(test_db):
    """Create test user and return user_id."""
    user_id = uuid4()
    test_db.execute(
        """
        INSERT INTO users (id, email, name, picture, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [str(user_id), "test@example.com", "Test User", None, datetime.now()],
    )
    return user_id


@pytest.fixture
def sample_entry(test_db, test_user_id):
    """Create a sample entry for testing."""
    entry_data = EntryCreate(
        date="2024-12-10",
        conversations=[
            Conversation(
                id=uuid4(),
                started_at=datetime.now(timezone.utc),
                messages=[
                    Message(
                        role="user",
                        content="Test message",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                prompt_source="user",
            )
        ],
        refined_output="Original content",
    )

    entry = entry_repo.create_entry(test_db, test_user_id, entry_data)
    return entry


class TestVersionSnapshotCreation:
    """Tests for version snapshot creation on update."""

    def test_version_created_on_update(self, test_db, test_user_id, sample_entry):
        """Should create version snapshot when entry is updated."""
        from app.models.entry import EntryUpdate

        # Verify no versions initially
        versions_before = entry_repo.get_entry_versions(
            test_db, sample_entry.id, test_user_id
        )
        assert len(versions_before) == 0

        # Update entry
        update_data = EntryUpdate(refined_output="Updated content")
        entry_repo.update_entry(test_db, sample_entry.id, test_user_id, update_data)

        # Verify version was created
        versions_after = entry_repo.get_entry_versions(
            test_db, sample_entry.id, test_user_id
        )
        assert len(versions_after) == 1

    def test_version_snapshot_contains_previous_content(
        self, test_db, test_user_id, sample_entry
    ):
        """Version snapshot should contain the content before update."""
        from app.models.entry import EntryUpdate

        original_content = sample_entry.refined_output

        # Update entry
        update_data = EntryUpdate(refined_output="New content")
        entry_repo.update_entry(test_db, sample_entry.id, test_user_id, update_data)

        # Get version
        versions = entry_repo.get_entry_versions(test_db, sample_entry.id, test_user_id)
        assert len(versions) == 1
        assert versions[0].content_snapshot == original_content
        assert versions[0].version == 1  # Original version number

    def test_multiple_updates_create_multiple_versions(
        self, test_db, test_user_id, sample_entry
    ):
        """Each update should create a new version snapshot."""
        from app.models.entry import EntryUpdate

        # Update multiple times
        for i in range(3):
            update_data = EntryUpdate(refined_output=f"Content version {i + 2}")
            entry_repo.update_entry(test_db, sample_entry.id, test_user_id, update_data)

        # Verify all versions were created
        versions = entry_repo.get_entry_versions(test_db, sample_entry.id, test_user_id)
        assert len(versions) == 3

        # Versions should be in descending order (newest first)
        assert versions[0].version == 3
        assert versions[1].version == 2
        assert versions[2].version == 1


class TestVersionHistoryRetrieval:
    """Tests for retrieving version history."""

    def test_get_versions_returns_all_versions(
        self, test_db, test_user_id, sample_entry
    ):
        """Should return all version snapshots for an entry."""
        from app.models.entry import EntryUpdate

        # Create some versions
        contents = ["First update", "Second update", "Third update"]
        for content in contents:
            entry_repo.update_entry(
                test_db, sample_entry.id, test_user_id, EntryUpdate(refined_output=content)
            )

        # Get versions
        versions = entry_repo.get_entry_versions(test_db, sample_entry.id, test_user_id)

        assert len(versions) == 3
        # Should be ordered from newest to oldest
        assert versions[0].version > versions[-1].version

    def test_get_versions_empty_for_new_entry(self, test_db, test_user_id, sample_entry):
        """Should return empty list for entry without updates."""
        versions = entry_repo.get_entry_versions(test_db, sample_entry.id, test_user_id)
        assert len(versions) == 0

    def test_get_versions_returns_empty_for_nonexistent_entry(
        self, test_db, test_user_id
    ):
        """Should return empty list for non-existent entry."""
        fake_id = uuid4()
        versions = entry_repo.get_entry_versions(test_db, fake_id, test_user_id)
        assert versions == []


class TestVersionIntegrity:
    """Tests for version snapshot immutability and integrity."""

    def test_version_snapshots_are_immutable(
        self, test_db, test_user_id, sample_entry
    ):
        """Version snapshots should not change after creation."""
        from app.models.entry import EntryUpdate

        # Create a version
        entry_repo.update_entry(
            test_db,
            sample_entry.id,
            test_user_id,
            EntryUpdate(refined_output="First update"),
        )

        # Get the version
        versions_before = entry_repo.get_entry_versions(
            test_db, sample_entry.id, test_user_id
        )
        assert len(versions_before) == 1
        original_snapshot = versions_before[0].content_snapshot

        # Create another version
        entry_repo.update_entry(
            test_db,
            sample_entry.id,
            test_user_id,
            EntryUpdate(refined_output="Second update"),
        )

        # Get versions again
        versions_after = entry_repo.get_entry_versions(
            test_db, sample_entry.id, test_user_id
        )
        assert len(versions_after) == 2

        # Original version should be unchanged
        original_version = [v for v in versions_after if v.version == 1][0]
        assert original_version.content_snapshot == original_snapshot

    def test_version_contains_all_required_fields(
        self, test_db, test_user_id, sample_entry
    ):
        """Version snapshot should have all required fields."""
        from app.models.entry import EntryUpdate

        # Create a version
        entry_repo.update_entry(
            test_db, sample_entry.id, test_user_id, EntryUpdate(refined_output="Update")
        )

        # Get version
        versions = entry_repo.get_entry_versions(test_db, sample_entry.id, test_user_id)
        version = versions[0]

        # Verify all fields are present
        assert version.id is not None
        assert version.entry_id == sample_entry.id
        assert version.version == 1
        assert version.content_snapshot is not None
        assert version.created_at is not None
