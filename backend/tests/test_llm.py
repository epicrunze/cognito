"""LLM client tests — OllamaClient, retries, fallback."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.llm import GeminiClient, LLMError, OllamaClient, get_llm_client


# ── get_llm_client routing ─────────────────────────────────────────────


def test_get_llm_client_gemini_default():
    with patch.object(GeminiClient, "__init__", return_value=None):
        client = get_llm_client()
        assert isinstance(client, GeminiClient)


def test_get_llm_client_ollama_by_model():
    client = get_llm_client(model="qwen3:4b")
    assert isinstance(client, OllamaClient)


def test_get_llm_client_ollama_by_name():
    client = get_llm_client(model="ollama-qwen")
    assert isinstance(client, OllamaClient)


def test_get_llm_client_confidential():
    client = get_llm_client(confidential=True)
    assert isinstance(client, OllamaClient)


def test_get_llm_client_no_gemini_key():
    """Falls back to Ollama when Gemini API key is missing."""
    with patch("app.services.llm.settings") as mock_settings:
        mock_settings.gemini_api_key = ""
        mock_settings.ollama_url = "http://localhost:11434"
        mock_settings.ollama_model = "qwen3:4b"
        client = get_llm_client()
        assert isinstance(client, OllamaClient)


# ── OllamaClient ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ollama_generate():
    client = OllamaClient(base_url="http://test:11434", model="test-model")
    mock_response = {"message": {"content": "Hello world"}}
    with patch.object(client, "_call_api", new_callable=AsyncMock, return_value=mock_response):
        result = await client.generate(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="You are helpful.",
        )
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_ollama_generate_with_tools_no_calls():
    client = OllamaClient(base_url="http://test:11434", model="test-model")
    mock_response = {"message": {"content": "Done!", "tool_calls": []}}
    with patch.object(client, "_call_api", new_callable=AsyncMock, return_value=mock_response):
        result = await client.generate_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="sys",
            tools=[],
            tool_handler=AsyncMock(),
        )
    assert result == "Done!"


@pytest.mark.asyncio
async def test_ollama_generate_with_tools_calls():
    client = OllamaClient(base_url="http://test:11434", model="test-model")
    # First call: tool call. Second call: final response.
    responses = [
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "lookup", "arguments": {"q": "test"}}}
        ]}},
        {"message": {"content": "Result: found it"}},
    ]
    handler = AsyncMock(return_value={"id": 1, "title": "Test"})
    with patch.object(client, "_call_api", new_callable=AsyncMock, side_effect=responses):
        result = await client.generate_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="sys",
            tools=[{"name": "lookup", "description": "Look up", "parameters": {"q": {"type": "string"}}}],
            tool_handler=handler,
        )
    assert result == "Result: found it"
    handler.assert_awaited_once_with("lookup", {"q": "test"})


# ── Gemini retry on 429 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gemini_retry_on_429():
    """Gemini retries up to 3 times on 429 and eventually raises."""
    client = GeminiClient(api_key="test-key", model="test-model")
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMError, match="429"):
                await client._call_api({"test": True})
