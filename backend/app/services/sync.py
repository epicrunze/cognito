"""
Sync service for handling offline-first synchronization.

Implements last-write-wins conflict resolution and pending message processing.
"""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.logging import get_logger, info, debug, warning, error
from app.models.entry import Entry, EntryCreate, EntryUpdate, Conversation, Message
from app.models.goal import Goal, GoalCreate, GoalUpdate
from app.repositories import entry_repo, goal_repo
from app.services.chat import ChatService
from app.utils.timestamp import utc_now, compare_timestamps, parse_iso_timestamp

logger = get_logger("sync")


class SyncService:
    """
    Service for processing sync requests.
    
    Handles:
    - Processing pending changes from client
    - Last-write-wins conflict resolution based on updated_at
    - Detecting and processing pending chat messages
    - Returning server changes since last sync
    """
    
    def __init__(self, conn, user_id: UUID):
        """
        Initialize sync service.
        
        Args:
            conn: Database connection
            user_id: Current user's ID
        """
        self.conn = conn
        self.user_id = user_id
    
    def process_pending_changes(
        self,
        pending_changes: list[dict],
        base_versions: dict[str, int]
    ) -> tuple[list[str], list[str]]:
        """
        Process pending changes from client.
        
        Uses last-write-wins based on updated_at timestamp.
        
        Args:
            pending_changes: List of pending change objects
            base_versions: Map of entity_id -> version for conflict detection
        
        Returns:
            Tuple of (applied_ids, skipped_ids)
        """
        applied: list[str] = []
        skipped: list[str] = []
        
        for change in pending_changes:
            try:
                entity = change.get("entity")
                entity_id = change.get("entity_id")
                change_type = change.get("type")
                data = change.get("data", {})
                client_timestamp = change.get("timestamp")
                
                debug(
                    "Processing change",
                    entity=entity,
                    entity_id=entity_id,
                    type=change_type
                )
                
                if entity == "entry":
                    if self._process_entry_change(change_type, entity_id, data, client_timestamp, base_versions):
                        applied.append(entity_id)
                    else:
                        skipped.append(entity_id)
                elif entity == "goal":
                    if self._process_goal_change(change_type, entity_id, data, client_timestamp):
                        applied.append(entity_id)
                    else:
                        skipped.append(entity_id)
                else:
                    warning(f"Unknown entity type: {entity}")
                    skipped.append(entity_id)
                    
            except Exception as e:
                error(f"Failed to process change: {e}", entity_id=change.get("entity_id"))
                skipped.append(change.get("entity_id", "unknown"))
        
        info(f"Sync processed: {len(applied)} applied, {len(skipped)} skipped")
        return applied, skipped
    
    def _process_entry_change(
        self,
        change_type: str,
        entity_id: str,
        data: dict,
        client_timestamp: Optional[str],
        base_versions: dict[str, int]
    ) -> bool:
        """
        Process a single entry change.
        
        Returns:
            True if change was applied, False if skipped
        """
        try:
            entry_uuid = UUID(entity_id)
        except (ValueError, TypeError):
            error(f"Invalid entry ID: {entity_id}")
            return False
        
        existing = entry_repo.get_entry_by_id(self.conn, entry_uuid, self.user_id)
        
        if change_type == "create":
            if existing:
                # Entry already exists, check if we should update
                return self._should_apply_update(existing, client_timestamp)
            
            # Create new entry
            entry_data = EntryCreate(
                date=data.get("date", datetime.now().strftime("%Y-%m-%d")),
                conversations=self._parse_conversations(data.get("conversations", [])),
                refined_output=data.get("refined_output", "")
            )
            entry_repo.create_entry(self.conn, entry_data, self.user_id, entry_id=entry_uuid)
            debug(f"Created entry: {entity_id}")
            return True
            
        elif change_type == "update":
            if not existing:
                # Entry doesn't exist, create it
                entry_data = EntryCreate(
                    date=data.get("date", datetime.now().strftime("%Y-%m-%d")),
                    conversations=self._parse_conversations(data.get("conversations", [])),
                    refined_output=data.get("refined_output", "")
                )
                entry_repo.create_entry(self.conn, entry_data, self.user_id, entry_id=entry_uuid)
                debug(f"Created entry from update: {entity_id}")
                return True
            
            # Check last-write-wins
            if not self._should_apply_update(existing, client_timestamp):
                debug(f"Skipping update - server is newer: {entity_id}")
                return False
            
            # Apply update
            update_data = EntryUpdate(
                conversations=self._parse_conversations(data.get("conversations")) if data.get("conversations") is not None else None,
                refined_output=data.get("refined_output"),
                relevance_score=data.get("relevance_score"),
                status=data.get("status")
            )
            entry_repo.update_entry(self.conn, entry_uuid, self.user_id, update_data)
            debug(f"Updated entry: {entity_id}")
            return True
            
        elif change_type == "delete":
            if existing:
                # Soft delete by archiving
                update_data = EntryUpdate(status="archived")
                entry_repo.update_entry(self.conn, entry_uuid, self.user_id, update_data)
                debug(f"Archived entry: {entity_id}")
            return True
        
        return False
    
    def _process_goal_change(
        self,
        change_type: str,
        entity_id: str,
        data: dict,
        client_timestamp: Optional[str]
    ) -> bool:
        """
        Process a single goal change.
        
        Returns:
            True if change was applied, False if skipped
        """
        try:
            goal_uuid = UUID(entity_id)
        except (ValueError, TypeError):
            error(f"Invalid goal ID: {entity_id}")
            return False
        
        existing = goal_repo.get_goal_by_id(self.conn, goal_uuid, self.user_id)
        
        if change_type == "create":
            if existing:
                return self._should_apply_update(existing, client_timestamp)
            
            goal_data = GoalCreate(
                category=data.get("category", "general"),
                description=data.get("description", "")
            )
            goal_repo.create_goal(self.conn, goal_data, self.user_id, goal_id=goal_uuid)
            debug(f"Created goal: {entity_id}")
            return True
            
        elif change_type == "update":
            if not existing:
                goal_data = GoalCreate(
                    category=data.get("category", "general"),
                    description=data.get("description", "")
                )
                goal_repo.create_goal(self.conn, goal_data, self.user_id, goal_id=goal_uuid)
                debug(f"Created goal from update: {entity_id}")
                return True
            
            if not self._should_apply_update(existing, client_timestamp):
                debug(f"Skipping goal update - server is newer: {entity_id}")
                return False
            
            update_data = GoalUpdate(
                category=data.get("category"),
                description=data.get("description"),
                active=data.get("active")
            )
            goal_repo.update_goal(self.conn, goal_uuid, self.user_id, update_data)
            debug(f"Updated goal: {entity_id}")
            return True
            
        elif change_type == "delete":
            if existing:
                goal_repo.delete_goal(self.conn, goal_uuid, self.user_id)
                debug(f"Deleted goal: {entity_id}")
            return True
        
        return False
    
    def _should_apply_update(self, existing, client_timestamp: Optional[str]) -> bool:
        """
        Determine if client update should be applied (last-write-wins).
        
        Uses centralized timestamp comparison utility.
        
        Args:
            existing: Existing entity from database (Entry or Goal)
            client_timestamp: Client's updated_at timestamp (ISO 8601)
        
        Returns:
            True if client change is newer and should be applied
        """
        return compare_timestamps(client_timestamp, existing.updated_at)
    
    def _parse_conversations(self, conversations_data: Optional[list]) -> list[Conversation]:
        """Parse conversations from JSON data."""
        if not conversations_data:
            return []
        
        result = []
        for conv_data in conversations_data:
            if isinstance(conv_data, Conversation):
                result.append(conv_data)
            elif isinstance(conv_data, dict):
                # Parse messages
                messages = []
                for msg_data in conv_data.get("messages", []):
                    if isinstance(msg_data, Message):
                        messages.append(msg_data)
                    elif isinstance(msg_data, dict):
                        messages.append(Message(
                            role=msg_data.get("role", "user"),
                            content=msg_data.get("content", ""),
                            timestamp=parse_iso_timestamp(
                                msg_data.get("timestamp", utc_now().isoformat())
                            )
                        ))
                
                conv = Conversation(
                    id=UUID(conv_data.get("id")) if isinstance(conv_data.get("id"), str) else conv_data.get("id", uuid4()),
                    started_at=parse_iso_timestamp(
                        conv_data.get("started_at", utc_now().isoformat())
                    ),
                    messages=messages,
                    prompt_source=conv_data.get("prompt_source", "user"),
                    notification_id=UUID(conv_data.get("notification_id")) if conv_data.get("notification_id") else None
                )
                result.append(conv)
        
        return result
    
    def get_server_changes(
        self,
        last_synced_at: Optional[str]
    ) -> dict[str, list]:
        """
        Get server changes since last sync.
        
        Args:
            last_synced_at: ISO timestamp of last sync, or None for full sync
        
        Returns:
            Dict with 'entries' and 'goals' lists
        """
        since_dt = None
        if last_synced_at:
            try:
                since_dt = parse_iso_timestamp(last_synced_at)
            except ValueError:
                warning(f"Invalid last_synced_at timestamp: {last_synced_at}")
        
        # Get all entries/goals for user (filtered by updated_at if since_dt provided)
        entries = entry_repo.get_entries_since(self.conn, self.user_id, since_dt)
        goals = goal_repo.get_goals_since(self.conn, self.user_id, since_dt)
        
        debug(f"Server changes: {len(entries)} entries, {len(goals)} goals")
        
        return {
            "entries": [self._entry_to_dict(e) for e in entries],
            "goals": [self._goal_to_dict(g) for g in goals]
        }
    
    async def process_pending_messages(self) -> list[str]:
        """
        Process entries with pending messages that need LLM responses.
        
        Delegates to ChatService for unified LLM handling.
        
        Returns:
            List of entry IDs that were processed
        """
        processed_entries: list[str] = []
        chat_service = ChatService(self.conn, self.user_id)
        
        # Get all active entries for user
        entries = entry_repo.list_entries(self.conn, self.user_id)
        
        for entry in entries:
            if await chat_service.process_pending_chat(entry):
                processed_entries.append(str(entry.id))
        
        return processed_entries
    
    async def process_pending_refines(self, limit: int = 5) -> list[str]:
        """
        Process entries queued for refinement.
        
        Processes entries with pending_refine=True using ChatService.
        
        Args:
            limit: Maximum entries to process per call
        
        Returns:
            List of entry IDs that were processed
        """
        processed_entries: list[str] = []
        chat_service = ChatService(self.conn, self.user_id)
        
        # Get entries pending refine
        entries = entry_repo.get_entries_pending_refine(self.conn, self.user_id, limit)
        
        for entry in entries:
            if await chat_service.process_pending_refine(entry):
                processed_entries.append(str(entry.id))
        
        info(f"Processed {len(processed_entries)} pending refines")
        return processed_entries
    
    def _entry_to_dict(self, entry: Entry) -> dict:
        """Convert entry to dictionary for sync response."""
        return {
            "id": str(entry.id),
            "date": entry.date,
            "conversations": entry.conversations if isinstance(entry.conversations, list) else json.loads(entry.conversations) if entry.conversations else [],
            "refined_output": entry.refined_output,
            "relevance_score": entry.relevance_score,
            "last_interacted_at": entry.last_interacted_at.isoformat() if entry.last_interacted_at else None,
            "interaction_count": entry.interaction_count,
            "status": entry.status,
            "pending_refine": entry.pending_refine,
            "refine_status": entry.refine_status,
            "refine_error": entry.refine_error,
            "version": entry.version,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
        }
    
    def _goal_to_dict(self, goal: Goal) -> dict:
        """Convert goal to dictionary for sync response."""
        return {
            "id": str(goal.id),
            "category": goal.category,
            "description": goal.description,
            "active": goal.active,
            "created_at": goal.created_at.isoformat() if goal.created_at else None,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None
        }
