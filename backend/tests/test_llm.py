"""
Tests for LLM service.

Tests GeminiClient, OllamaClient, and LLMRouter with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm import (
    GeminiClient,
    OllamaClient,
    LLMRouter,
    CHAT_SYSTEM_PROMPT,
    REFINE_SYSTEM_PROMPT,
)


class TestGeminiClient:
    """Tests for GeminiClient."""

    def test_init_with_api_key(self):
        """Test client initialization with explicit API key."""
        client = GeminiClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "gemini-2.0-flash"

    def test_init_with_custom_model(self):
        """Test client initialization with custom model."""
        client = GeminiClient(api_key="test-key", model="gemini-1.5-pro")
        assert client.model == "gemini-1.5-pro"

    def test_init_without_api_key_raises(self):
        """Test that missing API key raises ValueError."""
        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            with pytest.raises(ValueError, match="API key is required"):
                GeminiClient()

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello! How can I help you today?"}]
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            result = await client.generate(messages, "Be helpful")

            assert result == "Hello! How can I help you today?"

    @pytest.mark.asyncio
    async def test_generate_empty_candidates_raises(self):
        """Test that empty candidates raises ValueError."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(ValueError, match="No candidates"):
                await client.generate(messages, "Be helpful")

    @pytest.mark.asyncio
    async def test_generate_converts_roles(self):
        """Test that assistant role is converted to model for Gemini."""
        client = GeminiClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Response"}]
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
                {"role": "user", "content": "How are you?"},
            ]
            await client.generate(messages, "Be helpful")

            # Check the payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["contents"][0]["role"] == "user"
            assert payload["contents"][1]["role"] == "model"  # assistant -> model
            assert payload["contents"][2]["role"] == "user"


class TestOllamaClient:
    """Tests for OllamaClient."""

    def test_init_defaults(self):
        """Test client initialization with defaults."""
        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.ollama_url = "http://localhost:11434"
            client = OllamaClient()
            assert client.base_url == "http://localhost:11434"
            assert client.model == "llama3.2"

    def test_init_with_custom_url(self):
        """Test client initialization with custom URL."""
        client = OllamaClient(base_url="http://custom:8080/")
        assert client.base_url == "http://custom:8080"  # Trailing slash stripped

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "I'm doing well, thanks!"
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "How are you?"}]
            result = await client.generate(messages, "Be friendly")

            assert result == "I'm doing well, thanks!"

    @pytest.mark.asyncio
    async def test_generate_includes_system_prompt(self):
        """Test that system prompt is included in messages."""
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Response"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            await client.generate(messages, "Be a helpful assistant")

            # Check the payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["messages"][0]["role"] == "system"
            assert payload["messages"][0]["content"] == "Be a helpful assistant"
            assert payload["messages"][1]["role"] == "user"


class TestLLMRouter:
    """Tests for LLMRouter."""

    def test_init(self):
        """Test router initialization."""
        router = LLMRouter()
        assert router._gemini_client is None
        assert router._ollama_client is None

    @pytest.mark.asyncio
    async def test_generate_uses_gemini_by_default(self):
        """Test that Gemini is used when use_local_model is False."""
        router = LLMRouter()

        with patch.object(GeminiClient, "__init__", return_value=None):
            with patch.object(GeminiClient, "generate", new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = "Gemini response"

                result = await router.generate(
                    messages=[{"role": "user", "content": "Hello"}],
                    system_prompt="Test",
                    use_local_model=False,
                )

                assert result == "Gemini response"
                mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_uses_ollama_when_local(self):
        """Test that Ollama is used when use_local_model is True."""
        router = LLMRouter()

        with patch.object(OllamaClient, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Ollama response"

            result = await router.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="Test",
                use_local_model=True,
            )

            assert result == "Ollama response"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_uses_chat_prompt(self):
        """Test that chat method uses CHAT_SYSTEM_PROMPT."""
        router = LLMRouter()

        with patch.object(router, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Chat response"

            messages = [{"role": "user", "content": "Hello"}]
            await router.chat(messages, use_local_model=False)

            mock_generate.assert_called_once_with(
                messages, CHAT_SYSTEM_PROMPT, False
            )

    @pytest.mark.asyncio
    async def test_refine_uses_refine_prompt(self):
        """Test that refine method uses REFINE_SYSTEM_PROMPT."""
        router = LLMRouter()

        with patch.object(router, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Refined output"

            await router.refine("Some conversation text", use_local_model=False)

            call_args = mock_generate.call_args
            assert call_args[0][1] == REFINE_SYSTEM_PROMPT


class TestSystemPrompts:
    """Tests for system prompt constants."""

    def test_chat_prompt_exists(self):
        """Test that chat system prompt is defined."""
        assert CHAT_SYSTEM_PROMPT
        assert "journaling" in CHAT_SYSTEM_PROMPT.lower()
        assert "follow-up" in CHAT_SYSTEM_PROMPT.lower()

    def test_refine_prompt_exists(self):
        """Test that refine system prompt is defined."""
        assert REFINE_SYSTEM_PROMPT
        assert "synthesize" in REFINE_SYSTEM_PROMPT.lower()
        assert "markdown" in REFINE_SYSTEM_PROMPT.lower()
