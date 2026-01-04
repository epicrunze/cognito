"""
Tests for Chat router.

Tests chat endpoints with mocked LLM responses.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_schema, get_db
from app.models.entry import Conversation, Message


# Test fixtures
@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user."""
    return {
        "id": uuid4(),
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def auth_override(test_user):
    """Override authentication for testing."""
    from app.models.user import User

    async def mock_get_current_user():
        return User(
            email=test_user["email"],
            name=test_user["name"],
        )

    return mock_get_current_user


@pytest.fixture
def setup_test_db(test_db_path, test_user):
    """Set up a test database with schema and test user."""
    import duckdb

    conn = duckdb.connect(test_db_path)
    init_schema(conn)

    # Create test user
    conn.execute(
        """
        INSERT INTO users (id, email, name)
        VALUES (?, ?, ?)
        """,
        [str(test_user["id"]), test_user["email"], test_user["name"]],
    )

    conn.close()
    return test_db_path


@pytest.fixture
def test_entry(test_user):
    """Create test entry data."""
    return {
        "id": uuid4(),
        "user_id": test_user["id"],
        "date": "2024-12-25",
        "conversations": [],
        "refined_output": "",
    }


@pytest.fixture
def setup_test_entry(setup_test_db, test_entry):
    """Set up a test entry in the database."""
    import duckdb

    conn = duckdb.connect(setup_test_db)
    conn.execute(
        """
        INSERT INTO entries (id, user_id, date, conversations, refined_output)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            str(test_entry["id"]),
            str(test_entry["user_id"]),
            test_entry["date"],
            json.dumps(test_entry["conversations"]),
            test_entry["refined_output"],
        ],
    )
    conn.close()
    return test_entry


class TestChatEndpoint:
    """Tests for POST /api/chat endpoint."""

    def test_chat_requires_authentication(self, client):
        """Test that chat endpoint requires authentication."""
        response = client.post(
            "/api/chat",
            json={
                "entry_id": str(uuid4()),
                "message": "Hello",
            },
        )
        assert response.status_code == 401

    def test_chat_entry_not_found(self, client, auth_override, setup_test_db):
        """Test chat with non-existent entry."""
        from app.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            import duckdb

            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            response = client.post(
                "/api/chat",
                json={
                    "entry_id": str(uuid4()),
                    "message": "Hello",
                },
            )
            conn.close()

        app.dependency_overrides.clear()
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_chat_creates_new_conversation(
        self, client, auth_override, setup_test_db, setup_test_entry
    ):
        """Test that chat creates a new conversation when conversation_id is not provided."""
        from app.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            import duckdb

            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            with patch("app.services.chat.llm_router") as mock_llm:
                mock_llm.chat = AsyncMock(return_value="Hello! How are you feeling today?")

                response = client.post(
                    "/api/chat",
                    json={
                        "entry_id": str(setup_test_entry["id"]),
                        "message": "Hello",
                    },
                )

            conn.close()

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert data["response"] == "Hello! How are you feeling today?"

    def test_chat_continues_existing_conversation(
        self, client, auth_override, setup_test_db, test_entry, test_user
    ):
        """Test that chat continues an existing conversation."""
        import duckdb
        from app.auth.dependencies import get_current_user

        # Create entry with existing conversation
        conversation_id = uuid4()
        conversations = [
            {
                "id": str(conversation_id),
                "started_at": datetime.utcnow().isoformat(),
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": datetime.utcnow().isoformat()},
                    {"role": "assistant", "content": "Hi there!", "timestamp": datetime.utcnow().isoformat()},
                ],
                "prompt_source": "user",
                "notification_id": None,
            }
        ]

        conn = duckdb.connect(setup_test_db)
        conn.execute(
            """
            INSERT INTO entries (id, user_id, date, conversations, refined_output)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                str(test_entry["id"]),
                str(test_user["id"]),
                test_entry["date"],
                json.dumps(conversations),
                "",
            ],
        )
        conn.close()

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            with patch("app.services.chat.llm_router") as mock_llm:
                mock_llm.chat = AsyncMock(return_value="I'm doing well, thanks for asking!")

                response = client.post(
                    "/api/chat",
                    json={
                        "entry_id": str(test_entry["id"]),
                        "conversation_id": str(conversation_id),
                        "message": "How are you?",
                    },
                )

            conn.close()

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == str(conversation_id)

    def test_chat_conversation_not_found(
        self, client, auth_override, setup_test_db, setup_test_entry
    ):
        """Test chat with non-existent conversation ID."""
        from app.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            import duckdb

            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            response = client.post(
                "/api/chat",
                json={
                    "entry_id": str(setup_test_entry["id"]),
                    "conversation_id": str(uuid4()),  # Non-existent
                    "message": "Hello",
                },
            )
            conn.close()

        app.dependency_overrides.clear()
        assert response.status_code == 404
        assert "conversation" in response.json()["detail"].lower()

    def test_chat_llm_error_returns_503(
        self, client, auth_override, setup_test_db, setup_test_entry
    ):
        """Test that LLM errors return 503."""
        from app.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            import duckdb

            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            with patch("app.services.chat.llm_router") as mock_llm:
                mock_llm.chat = AsyncMock(side_effect=Exception("API error"))

                response = client.post(
                    "/api/chat",
                    json={
                        "entry_id": str(setup_test_entry["id"]),
                        "message": "Hello",
                    },
                )

            conn.close()

        app.dependency_overrides.clear()
        assert response.status_code == 503
        assert "LLM service error" in response.json()["detail"]


class TestRefineEndpoint:
    """Tests for POST /api/chat/refine endpoint."""

    def test_refine_requires_authentication(self, client):
        """Test that refine endpoint requires authentication."""
        response = client.post(
            "/api/chat/refine",
            json={"entry_id": str(uuid4())},
        )
        assert response.status_code == 401

    def test_refine_entry_not_found(self, client, auth_override, setup_test_db):
        """Test refine with non-existent entry."""
        from app.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            import duckdb

            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            response = client.post(
                "/api/chat/refine",
                json={"entry_id": str(uuid4())},
            )
            conn.close()

        app.dependency_overrides.clear()
        assert response.status_code == 404

    def test_refine_no_conversations_returns_400(
        self, client, auth_override, setup_test_db, setup_test_entry
    ):
        """Test that refine returns 400 when no conversations exist."""
        from app.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            import duckdb

            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            response = client.post(
                "/api/chat/refine",
                json={"entry_id": str(setup_test_entry["id"])},
            )
            conn.close()

        app.dependency_overrides.clear()
        assert response.status_code == 400
        assert "no conversations" in response.json()["detail"].lower()

    def test_refine_success(
        self, client, auth_override, setup_test_db, test_entry, test_user
    ):
        """Test successful refine operation."""
        import duckdb
        from app.auth.dependencies import get_current_user

        # Create entry with conversations
        conversations = [
            {
                "id": str(uuid4()),
                "started_at": datetime.utcnow().isoformat(),
                "messages": [
                    {"role": "user", "content": "I had a productive day", "timestamp": datetime.utcnow().isoformat()},
                    {"role": "assistant", "content": "That's wonderful!", "timestamp": datetime.utcnow().isoformat()},
                ],
                "prompt_source": "user",
                "notification_id": None,
            }
        ]

        conn = duckdb.connect(setup_test_db)
        conn.execute(
            """
            INSERT INTO entries (id, user_id, date, conversations, refined_output)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                str(test_entry["id"]),
                str(test_user["id"]),
                test_entry["date"],
                json.dumps(conversations),
                "",
            ],
        )
        conn.close()

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            with patch("app.services.chat.llm_router") as mock_llm:
                mock_llm.refine = AsyncMock(
                    return_value="# Today's Reflection\n\nI had a productive day and felt accomplished."
                )

                response = client.post(
                    "/api/chat/refine",
                    json={"entry_id": str(test_entry["id"])},
                )

            conn.close()

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "refined_output" in data
        assert "Today's Reflection" in data["refined_output"]

    def test_refine_llm_error_returns_503(
        self, client, auth_override, setup_test_db, test_entry, test_user
    ):
        """Test that LLM errors during refine return 503."""
        import duckdb
        from app.auth.dependencies import get_current_user

        # Create entry with conversations
        conversations = [
            {
                "id": str(uuid4()),
                "started_at": datetime.utcnow().isoformat(),
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": datetime.utcnow().isoformat()},
                ],
                "prompt_source": "user",
                "notification_id": None,
            }
        ]

        conn = duckdb.connect(setup_test_db)
        conn.execute(
            """
            INSERT INTO entries (id, user_id, date, conversations, refined_output)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                str(test_entry["id"]),
                str(test_user["id"]),
                test_entry["date"],
                json.dumps(conversations),
                "",
            ],
        )
        conn.close()

        app.dependency_overrides[get_current_user] = auth_override

        with patch("app.routers.chat.get_db") as mock_get_db:
            conn = duckdb.connect(setup_test_db)
            mock_get_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=None)

            with patch("app.services.chat.llm_router") as mock_llm:
                mock_llm.refine = AsyncMock(side_effect=Exception("API error"))

                response = client.post(
                    "/api/chat/refine",
                    json={"entry_id": str(test_entry["id"])},
                )

            conn.close()

        app.dependency_overrides.clear()
        assert response.status_code == 503


class TestChatContextBuilding:
    """Tests for conversation context building."""

    def test_context_includes_all_messages(self):
        """Test that context includes all messages from conversation."""
        from app.routers.chat import _build_context_messages

        conversations = [
            Conversation(
                id=uuid4(),
                started_at=datetime.utcnow(),
                messages=[
                    Message(role="user", content="Hello", timestamp=datetime.utcnow()),
                    Message(role="assistant", content="Hi!", timestamp=datetime.utcnow()),
                    Message(role="user", content="How are you?", timestamp=datetime.utcnow()),
                ],
                prompt_source="user",
                notification_id=None,
            )
        ]

        messages = _build_context_messages(conversations)

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_format_conversations_for_refine(self):
        """Test conversation formatting for refine prompt."""
        from app.routers.chat import _format_conversations_for_refine

        conversations = [
            Conversation(
                id=uuid4(),
                started_at=datetime.utcnow(),
                messages=[
                    Message(role="user", content="I feel great today", timestamp=datetime.utcnow()),
                    Message(role="assistant", content="That's wonderful!", timestamp=datetime.utcnow()),
                ],
                prompt_source="user",
                notification_id=None,
            )
        ]

        result = _format_conversations_for_refine(conversations)

        assert "Conversation 1" in result
        assert "User" in result
        assert "I feel great today" in result
        assert "Assistant" in result
        assert "That's wonderful!" in result
