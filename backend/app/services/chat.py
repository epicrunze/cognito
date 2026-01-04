"""
Chat service for unified chat and refine operations.

Provides a single source of truth for LLM chat/refine logic,
used by both the Chat router and SyncService.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import httpx

from app.logging import get_logger, info, debug, warning, error
from app.models.entry import Conversation, Message, Entry, EntryUpdate
from app.repositories import entry_repo
from app.services.llm import llm_router
from app.utils.timestamp import utc_now

logger = get_logger("chat_service")

# Retry configuration for LLM calls
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0


class ChatServiceError(Exception):
    """Base exception for ChatService errors."""
    pass


class EntryNotFoundError(ChatServiceError):
    """Entry not found."""
    pass


class ConversationNotFoundError(ChatServiceError):
    """Conversation not found."""
    pass


class NoConversationsError(ChatServiceError):
    """No conversations to refine."""
    pass


class LLMError(ChatServiceError):
    """LLM service error."""
    pass


class ChatService:
    """
    Unified service for chat and refine operations.
    
    Handles:
    - Sending chat messages and getting LLM responses
    - Refining entries from conversations
    - Processing pending chat messages (for sync)
    - Processing pending refine operations (for sync)
    
    Includes internal retry logic with exponential backoff for 429 errors.
    """
    
    def __init__(self, conn, user_id: UUID):
        """
        Initialize ChatService.
        
        Args:
            conn: Database connection
            user_id: Current user's ID
        """
        self.conn = conn
        self.user_id = user_id
    
    async def _call_llm_with_retry(
        self,
        method: str,
        **kwargs
    ) -> str:
        """
        Call LLM with exponential backoff retry for 429 errors.
        
        Args:
            method: LLM method to call ('chat' or 'refine')
            **kwargs: Arguments to pass to the LLM method
            
        Returns:
            LLM response text
            
        Raises:
            LLMError: If all retries fail
        """
        backoff = INITIAL_BACKOFF_SECONDS
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                if method == "chat":
                    return await llm_router.chat(**kwargs)
                elif method == "refine":
                    return await llm_router.refine(**kwargs)
                else:
                    raise ValueError(f"Unknown LLM method: {method}")
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        warning(
                            f"Rate limited (429), retrying in {backoff}s",
                            attempt=attempt + 1,
                            max_retries=MAX_RETRIES
                        )
                        await asyncio.sleep(backoff)
                        backoff *= BACKOFF_MULTIPLIER
                        continue
                raise LLMError(f"LLM HTTP error: {e}")
                
            except Exception as e:
                raise LLMError(f"LLM error: {e}")
        
        raise LLMError(f"Max retries exceeded: {last_error}")
    
    def _parse_conversations(self, conversations_data) -> list[Conversation]:
        """Parse conversations from JSON or model list."""
        if not conversations_data:
            return []
        
        if isinstance(conversations_data, str):
            conversations_data = json.loads(conversations_data)
        
        result = []
        for conv_data in conversations_data:
            if isinstance(conv_data, Conversation):
                result.append(conv_data)
            elif isinstance(conv_data, dict):
                result.append(Conversation(**conv_data))
        
        return result
    
    def _format_conversations_for_refine(self, conversations: list[Conversation]) -> str:
        """Format all conversations as text for the refine prompt."""
        parts = []
        
        for i, conv in enumerate(conversations, 1):
            parts.append(f"## Conversation {i}")
            parts.append(f"Started: {conv.started_at.isoformat()}")
            parts.append("")
            
            for msg in conv.messages:
                role = "User" if msg.role == "user" else "Assistant"
                parts.append(f"**{role}:** {msg.content}")
                parts.append("")
            
            parts.append("---")
            parts.append("")
        
        return "\n".join(parts)
    
    async def send_message(
        self,
        entry_id: UUID,
        message: str,
        conversation_id: Optional[UUID] = None,
        use_local_model: bool = False
    ) -> dict:
        """
        Send a message and get an LLM response.
        
        Creates a new conversation if conversation_id is not provided.
        Stores both user message and assistant response in the entry.
        
        Args:
            entry_id: Entry ID
            message: User message content
            conversation_id: Optional conversation ID for continuing
            use_local_model: Whether to use local Ollama model
            
        Returns:
            Dict with 'response', 'conversation_id', 'entry_id'
            
        Raises:
            EntryNotFoundError: Entry not found
            ConversationNotFoundError: Conversation not found
            LLMError: LLM service error
        """
        # Get the entry
        entry = entry_repo.get_entry_by_id(self.conn, entry_id, self.user_id)
        if not entry:
            raise EntryNotFoundError(f"Entry {entry_id} not found")
        
        # Parse existing conversations
        conversations = self._parse_conversations(entry.conversations)
        
        # Find or create conversation
        current_conversation: Optional[Conversation] = None
        
        if conversation_id:
            # Find existing conversation
            for conv in conversations:
                if conv.id == conversation_id:
                    current_conversation = conv
                    break
            
            if not current_conversation:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
        else:
            # Create new conversation
            conversation_id = uuid4()
            current_conversation = Conversation(
                id=conversation_id,
                started_at=utc_now(),
                messages=[],
                prompt_source="user",
                notification_id=None,
            )
            conversations.append(current_conversation)
        
        # Add user message
        user_message = Message(
            role="user",
            content=message,
            timestamp=utc_now(),
        )
        current_conversation.messages.append(user_message)
        
        # Build context from all messages in this conversation
        context_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in current_conversation.messages
        ]
        
        # Get LLM response with retry
        response_text = await self._call_llm_with_retry(
            "chat",
            messages=context_messages,
            use_local_model=use_local_model
        )
        
        # Add assistant message
        assistant_message = Message(
            role="assistant",
            content=response_text,
            timestamp=utc_now(),
        )
        current_conversation.messages.append(assistant_message)
        
        # Update entry with modified conversations
        update_data = EntryUpdate(conversations=conversations)
        entry_repo.update_entry(self.conn, entry_id, self.user_id, update_data)
        
        info(f"Chat message processed for entry {entry_id}")
        
        return {
            "response": response_text,
            "conversation_id": conversation_id,
            "entry_id": entry_id,
        }
    
    async def refine_entry(
        self,
        entry_id: UUID,
        use_local_model: bool = False
    ) -> dict:
        """
        Generate a refined output from all conversations in an entry.
        
        Args:
            entry_id: Entry ID
            use_local_model: Whether to use local Ollama model
            
        Returns:
            Dict with 'refined_output', 'entry_id'
            
        Raises:
            EntryNotFoundError: Entry not found
            NoConversationsError: No conversations to refine
            LLMError: LLM service error
        """
        # Get the entry
        entry = entry_repo.get_entry_by_id(self.conn, entry_id, self.user_id)
        if not entry:
            raise EntryNotFoundError(f"Entry {entry_id} not found")
        
        # Parse conversations
        conversations = self._parse_conversations(entry.conversations)
        
        if not conversations:
            raise NoConversationsError("No conversations to refine")
        
        # Format conversations for the refine prompt
        conversations_text = self._format_conversations_for_refine(conversations)
        
        # Get refined output from LLM with retry
        refined_output = await self._call_llm_with_retry(
            "refine",
            conversations_text=conversations_text,
            use_local_model=use_local_model
        )
        
        # Update entry with refined output and clear pending_refine flag
        update_data = EntryUpdate(
            refined_output=refined_output,
        )
        entry_repo.update_entry(self.conn, entry_id, self.user_id, update_data)
        
        info(f"Entry {entry_id} refined successfully")
        
        return {
            "refined_output": refined_output,
            "entry_id": entry_id,
        }
    
    async def process_pending_chat(self, entry: Entry) -> bool:
        """
        Process pending chat messages in an entry.
        
        Scans messages for pending_response=True and generates LLM responses.
        
        Args:
            entry: Entry to process
            
        Returns:
            True if any messages were processed, False otherwise
        """
        conversations_data = entry.conversations
        if isinstance(conversations_data, str):
            conversations_data = json.loads(conversations_data)
        
        modified = False
        conversations = []
        
        for conv_data in conversations_data:
            if isinstance(conv_data, dict):
                messages = conv_data.get("messages", [])
                new_messages = []
                
                for msg in messages:
                    new_messages.append(msg)
                    
                    # Check if this message needs a response
                    if msg.get("pending_response") and msg.get("role") == "user":
                        debug(f"Processing pending message in entry {entry.id}")
                        
                        # Build context from conversation
                        context_messages = [
                            {"role": m.get("role"), "content": m.get("content")}
                            for m in new_messages
                        ]
                        
                        try:
                            # Get LLM response with retry
                            response_text = await self._call_llm_with_retry(
                                "chat",
                                messages=context_messages,
                                use_local_model=False
                            )
                            
                            # Add assistant response
                            assistant_msg = {
                                "role": "assistant",
                                "content": response_text,
                                "timestamp": utc_now().isoformat()
                            }
                            new_messages.append(assistant_msg)
                            
                            # Remove pending flag from original message
                            new_messages[-2]["pending_response"] = False
                            
                            modified = True
                            info(f"Added LLM response for entry {entry.id}")
                            
                        except LLMError as e:
                            error(f"LLM error for entry {entry.id}: {e}")
                            # Keep pending flag for retry
                
                conv_data["messages"] = new_messages
            
            conversations.append(conv_data)
        
        if modified:
            # Update entry with new conversations
            update_data = EntryUpdate(
                conversations=self._parse_conversations(conversations)
            )
            entry_repo.update_entry(self.conn, entry.id, self.user_id, update_data)
        
        return modified
    
    async def process_pending_refine(self, entry: Entry) -> bool:
        """
        Process pending refine for an entry.
        
        Args:
            entry: Entry with pending_refine=True
            
        Returns:
            True if refine was processed, False otherwise
        """
        try:
            # Mark as processing
            entry_repo.update_entry_refine_status(
                self.conn, entry.id, self.user_id, "processing", None
            )
            
            # Get conversations and refine
            conversations = self._parse_conversations(entry.conversations)
            
            if not conversations:
                entry_repo.update_entry_refine_status(
                    self.conn, entry.id, self.user_id, "failed", "No conversations to refine"
                )
                return False
            
            # Format and call LLM
            conversations_text = self._format_conversations_for_refine(conversations)
            refined_output = await self._call_llm_with_retry(
                "refine",
                conversations_text=conversations_text,
                use_local_model=False
            )
            
            # Update entry with refined output
            update_data = EntryUpdate(refined_output=refined_output)
            entry_repo.update_entry(self.conn, entry.id, self.user_id, update_data)
            
            # Mark as completed and clear pending flag
            entry_repo.update_entry_refine_status(
                self.conn, entry.id, self.user_id, "completed", None
            )
            entry_repo.clear_pending_refine(self.conn, entry.id, self.user_id)
            
            info(f"Pending refine completed for entry {entry.id}")
            return True
            
        except LLMError as e:
            error(f"LLM error during pending refine for entry {entry.id}: {e}")
            entry_repo.update_entry_refine_status(
                self.conn, entry.id, self.user_id, "failed", str(e)
            )
            return False
            
        except Exception as e:
            error(f"Error during pending refine for entry {entry.id}: {e}")
            entry_repo.update_entry_refine_status(
                self.conn, entry.id, self.user_id, "failed", str(e)
            )
            return False
