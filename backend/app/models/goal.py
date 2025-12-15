"""
Goal models for user objectives.

Pydantic models for Goal data representation following spec Section 3.3.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class GoalCreate(BaseModel):
    """Request model for creating a goal."""

    category: str  # 'health', 'productivity', 'skills', or custom
    description: str


class GoalUpdate(BaseModel):
    """Request model for updating a goal (partial updates)."""

    category: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class Goal(BaseModel):
    """Goal response model."""

    id: UUID
    category: str
    description: str
    active: bool = True
    created_at: datetime
    updated_at: datetime


class GoalInDB(Goal):
    """Goal with database-specific fields."""

    user_id: UUID
