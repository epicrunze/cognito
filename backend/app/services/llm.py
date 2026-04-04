"""
LLM service — Gemini client with tool-calling support.

Phase 1: Gemini API only.
Phase 2 will add OllamaClient with Qwen 3.x tool calling.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base LLM error."""


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(self, messages: list[dict], system_prompt: str) -> str:
        """Generate a plain text response."""

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], Any],
    ) -> str:
        """
        Generate using function/tool calling.

        The client will handle the multi-turn tool-call loop automatically:
          1. Send messages + tools to LLM
          2. If LLM calls a tool, invoke tool_handler(name, args)
          3. Feed tool result back, continue until LLM returns final text
        """


class GeminiClient(LLMClient):
    """Google Gemini API client using httpx."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        if not self.api_key:
            raise ValueError("Gemini API key is required")

    def _build_contents(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-style messages to Gemini contents format."""
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            content = msg["content"]
            if isinstance(content, str):
                contents.append({"role": role, "parts": [{"text": content}]})
            else:
                # Already in parts format (used for tool results)
                contents.append({"role": role, "parts": content})
        return contents

    def _build_tool_declarations(self, tools: list[dict]) -> list[dict]:
        """Convert our tool format to Gemini functionDeclarations."""
        declarations = []
        for tool in tools:
            decl: dict = {
                "name": tool["name"],
                "description": tool.get("description", ""),
            }
            params = tool.get("parameters", {})
            if params:
                properties = {}
                required = []
                for param_name, param_info in params.items():
                    prop: dict = {
                        "type": param_info.get("type", "string").upper(),
                        "description": param_info.get("description", ""),
                    }
                    if "items" in param_info:
                        prop["items"] = {"type": param_info["items"].get("type", "string").upper()}
                    properties[param_name] = prop
                    if param_info.get("required", False):
                        required.append(param_name)
                decl["parameters"] = {
                    "type": "OBJECT",
                    "properties": properties,
                }
                if required:
                    decl["parameters"]["required"] = required
            else:
                decl["parameters"] = {"type": "OBJECT", "properties": {}}
            declarations.append(decl)
        return declarations

    async def _call_api(self, payload: dict) -> dict:
        url = f"{self.API_BASE}/models/{self.model}:generateContent?key={self.api_key}"
        last_error = None
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(3):
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 429:
                        logger.warning("Gemini 429 rate-limited (attempt %d/3)", attempt + 1)
                        last_error = "429 rate-limited"
                        await asyncio.sleep(2 ** attempt)
                        continue
                    response.raise_for_status()
                    return response.json()
                except httpx.TimeoutException:
                    logger.warning("Gemini timeout (attempt %d/3)", attempt + 1)
                    last_error = "timeout"
                except httpx.HTTPStatusError as e:
                    logger.error("Gemini API error (attempt %d/3): %s %s",
                        attempt + 1, e.response.status_code, e.response.text[:500])
                    last_error = f"{e.response.status_code}: {e.response.text[:200]}"
                except httpx.ConnectError as e:
                    logger.error("Gemini connection error (attempt %d/3): %s", attempt + 1, e)
                    last_error = f"connection error: {e}"
                except Exception as e:
                    logger.error("Gemini unexpected error (attempt %d/3): %s: %s",
                        attempt + 1, type(e).__name__, e)
                    last_error = f"{type(e).__name__}: {e}"
        raise LLMError(f"Gemini API failed after 3 attempts (last: {last_error or 'unknown'})")

    async def generate(self, messages: list[dict], system_prompt: str) -> str:
        payload = {
            "contents": self._build_contents(messages),
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
        }
        data = await self._call_api(payload)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected Gemini response format: {e}\n{data}")

    async def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], Any],
    ) -> str:
        """
        Multi-turn tool-calling loop for Gemini.

        Continues calling the LLM until it produces a final text response
        (no more tool calls). Gemini native function calling is used.
        """
        contents = self._build_contents(messages)
        tool_declarations = self._build_tool_declarations(tools)

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "tools": [{"functionDeclarations": tool_declarations}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }

        # Tool-call loop — max 10 rounds to prevent infinite looping
        for _ in range(10):
            data = await self._call_api(payload)

            candidate = data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            if not parts:
                raise LLMError("Empty response from Gemini")

            # Check if there are any function calls in this response
            function_calls = [p for p in parts if "functionCall" in p]
            text_parts = [p for p in parts if "text" in p]

            if not function_calls:
                # Final text response — we're done
                if text_parts:
                    return text_parts[0]["text"]
                raise LLMError("Gemini returned no text and no function calls")

            # Append model's response (with function calls) to contents
            contents.append({"role": "model", "parts": parts})

            # Execute each tool call and collect results
            tool_response_parts = []
            for fc_part in function_calls:
                fc = fc_part["functionCall"]
                tool_name = fc["name"]
                tool_args = fc.get("args", {})

                try:
                    result = await tool_handler(tool_name, tool_args)
                except Exception as e:
                    result = {"error": str(e)}

                tool_response_parts.append({
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"result": result},
                    }
                })

            # Append tool results as a user turn
            contents.append({"role": "user", "parts": tool_response_parts})

            # Update payload for next iteration
            payload["contents"] = contents

        raise LLMError("Tool-calling loop exceeded maximum iterations")


class OllamaClient(LLMClient):
    """Ollama API client using httpx."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.ollama_model

    async def _call_api(self, payload: dict) -> dict:
        url = f"{self.base_url}/api/chat"
        last_error = None
        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(3):
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()
                except httpx.TimeoutException:
                    logger.warning("Ollama timeout (attempt %d/3)", attempt + 1)
                    last_error = "timeout"
                except httpx.ConnectError as e:
                    logger.error("Ollama connection error (attempt %d/3): %s", attempt + 1, e)
                    last_error = f"connection error: {e}"
                except httpx.HTTPStatusError as e:
                    logger.error("Ollama API error (attempt %d/3): %s", attempt + 1, e.response.status_code)
                    last_error = f"{e.response.status_code}"
                except Exception as e:
                    logger.error("Ollama unexpected error (attempt %d/3): %s", attempt + 1, e)
                    last_error = str(e)
                await asyncio.sleep(1)
        raise LLMError(f"Ollama API failed after 3 attempts (last: {last_error or 'unknown'})")

    async def generate(self, messages: list[dict], system_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": False,
            "options": {"temperature": 0.3},
        }
        data = await self._call_api(payload)
        try:
            return data["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected Ollama response format: {e}\n{data}")

    async def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], Any],
    ) -> str:
        ollama_tools = self._build_tools(tools)
        chat_messages = [{"role": "system", "content": system_prompt}] + messages

        for _ in range(10):
            payload = {
                "model": self.model,
                "messages": chat_messages,
                "stream": False,
                "tools": ollama_tools,
                "options": {"temperature": 0.2},
            }
            data = await self._call_api(payload)
            msg = data.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            if not tool_calls:
                return msg.get("content", "")

            chat_messages.append(msg)

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                tool_args = fn.get("arguments", {})
                try:
                    result = await tool_handler(tool_name, tool_args)
                except Exception as e:
                    result = {"error": str(e)}
                chat_messages.append({
                    "role": "tool",
                    "content": json.dumps(result) if not isinstance(result, str) else result,
                })

        raise LLMError("Ollama tool-calling loop exceeded maximum iterations")

    def _build_tools(self, tools: list[dict]) -> list[dict]:
        """Convert our tool format to Ollama's tool format."""
        result = []
        for tool in tools:
            properties = {}
            required = []
            for pname, pinfo in tool.get("parameters", {}).items():
                properties[pname] = {
                    "type": pinfo.get("type", "string"),
                    "description": pinfo.get("description", ""),
                }
                if pinfo.get("required", False):
                    required.append(pname)
            result.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return result


class FallbackClient(LLMClient):
    """Wraps a primary client with a fallback on failure."""

    def __init__(self, primary: LLMClient, fallback: LLMClient):
        self.primary = primary
        self.fallback = fallback

    async def generate(self, messages: list[dict], system_prompt: str) -> str:
        try:
            return await self.primary.generate(messages, system_prompt)
        except LLMError:
            logger.warning("Primary LLM failed, falling back to secondary")
            return await self.fallback.generate(messages, system_prompt)

    async def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], Any],
    ) -> str:
        try:
            return await self.primary.generate_with_tools(messages, system_prompt, tools, tool_handler)
        except LLMError:
            logger.warning("Primary LLM failed, falling back to secondary")
            return await self.fallback.generate_with_tools(messages, system_prompt, tools, tool_handler)


def get_llm_client(model: str | None = None, confidential: bool = False) -> LLMClient:
    """Return the appropriate LLM client based on model/confidential flag."""
    if confidential or (model and ("ollama" in model or model.startswith("qwen"))):
        return OllamaClient(model=model)
    # Gemini with Ollama fallback
    try:
        primary = GeminiClient(model=model)
    except ValueError:
        # No Gemini API key — use Ollama directly
        return OllamaClient(model=model)
    return primary
