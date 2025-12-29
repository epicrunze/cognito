"""
LLM Service for Cognito.

Provides clients for Gemini API and Ollama (local) with a router to select between them.
Follows spec Section 2.1.1 (LLM Router: Gemini API | Ollama).
"""

import httpx
from typing import Optional
from abc import ABC, abstractmethod

from app.config import settings


# System prompts for different use cases
CHAT_SYSTEM_PROMPT = """You are a thoughtful and empathetic journaling companion. Your role is to help the user explore their thoughts, feelings, and experiences through conversation.

Guidelines:
- Be warm, supportive, and non-judgmental
- Ask thoughtful follow-up questions to help deepen reflection
- Encourage self-discovery without being preachy
- Keep responses concise but meaningful (2-4 sentences typically)
- If the user shares something difficult, acknowledge their feelings first
- Help identify patterns or connections when appropriate
- Never give unsolicited advice unless asked

Remember: This is their journal. Your job is to help them think, not to tell them what to think."""

REFINE_SYSTEM_PROMPT = """You are a journal entry synthesizer. Your task is to take one or more conversations and create a coherent, well-written journal entry.

Guidelines:
- Write in first person from the user's perspective
- Capture the key themes, insights, and emotions from the conversations
- Organize content logically with clear paragraphs
- Use markdown formatting when appropriate (headers, bullet points)
- Preserve the user's voice and original insights
- Don't add new ideas that weren't in the conversations
- Keep the refined output concise but comprehensive
- Include any action items or decisions that were made

The output should read like a personal journal entry, not a transcript."""


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: System prompt to guide the LLM's behavior.

        Returns:
            The generated response text.
        """
        pass


class GeminiClient(LLMClient):
    """Client for Google Gemini API using httpx."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key. Defaults to settings.gemini_api_key.
            model: Model to use. Defaults to gemini-2.0-flash.
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or self.DEFAULT_MODEL

        if not self.api_key:
            raise ValueError("Gemini API key is required")

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> str:
        """Generate a response using Gemini API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: System prompt to guide the model.

        Returns:
            The generated response text.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
            ValueError: If the response format is unexpected.
        """
        # Build the request content
        # Gemini uses 'user' and 'model' roles (not 'assistant')
        contents = []

        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        # Build request payload
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        }

        url = f"{self.API_BASE}/models/{self.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            # Extract text from response
            try:
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates in Gemini response")

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise ValueError("No parts in Gemini response")

                return parts[0].get("text", "")
            except (KeyError, IndexError) as e:
                raise ValueError(f"Unexpected Gemini response format: {e}")


class OllamaClient(LLMClient):
    """Client for local Ollama API using httpx."""

    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama API base URL. Defaults to settings.ollama_url.
            model: Model to use. Defaults to llama3.2.
        """
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or self.DEFAULT_MODEL

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> str:
        """Generate a response using Ollama API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: System prompt to guide the model.

        Returns:
            The generated response text.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
            ValueError: If the response format is unexpected.
        """
        # Build messages with system prompt first
        ollama_messages = [
            {"role": "system", "content": system_prompt}
        ]

        for msg in messages:
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
            }
        }

        url = f"{self.base_url}/api/chat"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            try:
                return data["message"]["content"]
            except KeyError as e:
                raise ValueError(f"Unexpected Ollama response format: {e}")


class LLMRouter:
    """Router that selects between Gemini and Ollama based on configuration."""

    def __init__(self):
        """Initialize the LLM router with available clients."""
        self._gemini_client: Optional[GeminiClient] = None
        self._ollama_client: Optional[OllamaClient] = None

    def _get_gemini_client(self) -> GeminiClient:
        """Lazily initialize and return Gemini client."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient()
        return self._gemini_client

    def _get_ollama_client(self) -> OllamaClient:
        """Lazily initialize and return Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = OllamaClient()
        return self._ollama_client

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        use_local_model: bool = False,
    ) -> str:
        """Generate a response using the appropriate LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: System prompt to guide the model.
            use_local_model: If True, use Ollama. Otherwise use Gemini.

        Returns:
            The generated response text.
        """
        if use_local_model:
            client = self._get_ollama_client()
        else:
            client = self._get_gemini_client()

        return await client.generate(messages, system_prompt)

    async def chat(
        self,
        messages: list[dict],
        use_local_model: bool = False,
    ) -> str:
        """Generate a chat response using the chat system prompt.

        Args:
            messages: Conversation history.
            use_local_model: If True, use Ollama. Otherwise use Gemini.

        Returns:
            The assistant's response.
        """
        return await self.generate(messages, CHAT_SYSTEM_PROMPT, use_local_model)

    async def refine(
        self,
        conversations_text: str,
        use_local_model: bool = False,
    ) -> str:
        """Generate a refined journal entry from conversations.

        Args:
            conversations_text: Formatted text of all conversations.
            use_local_model: If True, use Ollama. Otherwise use Gemini.

        Returns:
            The refined journal entry.
        """
        messages = [
            {"role": "user", "content": conversations_text}
        ]
        return await self.generate(messages, REFINE_SYSTEM_PROMPT, use_local_model)


# Global router instance
llm_router = LLMRouter()
