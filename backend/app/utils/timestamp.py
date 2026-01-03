"""
Timestamp utilities for consistent UTC handling.

Provides centralized timestamp functions for the entire application to ensure
consistent timezone handling across all modules.
"""

from datetime import datetime, timezone
from typing import Optional, Union

from app.logging import get_logger, debug

logger = get_logger("timestamp")


def utc_now() -> datetime:
    """
    Get current UTC time as naive datetime (for database storage).
    
    DuckDB stores timestamps without timezone information, so we use naive
    datetimes that represent UTC time. When reading from the database,
    use ensure_utc() to add timezone info for comparisons.
    
    Returns:
        Naive datetime representing current UTC time
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_now_aware() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Use this when you need a timezone-aware datetime for comparisons
    or external APIs. For database storage, use utc_now() instead.
    
    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is UTC-aware. Treats naive datetimes as UTC.
    
    Use this when reading datetimes from the database to restore
    timezone information for comparisons.
    
    Args:
        dt: Datetime to normalize (may be naive or aware)
        
    Returns:
        Timezone-aware UTC datetime, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_iso_timestamp(ts: str) -> datetime:
    """
    Parse ISO 8601 timestamp to timezone-aware UTC datetime.
    
    Handles various formats:
    - 2024-12-30T12:00:00Z
    - 2024-12-30T12:00:00+00:00
    - 2024-12-30T12:00:00-05:00
    - 2024-12-30T12:00:00 (treated as UTC)
    
    Args:
        ts: ISO 8601 timestamp string
        
    Returns:
        Timezone-aware datetime in UTC
        
    Raises:
        ValueError: If timestamp cannot be parsed
    """
    # Handle Z suffix (Zulu time = UTC)
    ts = ts.replace("Z", "+00:00")
    
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError as e:
        raise ValueError(f"Cannot parse timestamp: {ts}") from e
    
    # If naive (no timezone), assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC
    return dt.astimezone(timezone.utc)


def compare_timestamps(
    client_ts: Optional[str],
    server_dt: datetime
) -> bool:
    """
    Determine if client timestamp is newer than or equal to server timestamp.
    
    Used for last-write-wins conflict resolution in sync.
    Both timestamps are normalized to UTC for comparison.
    
    Args:
        client_ts: Client's timestamp (ISO 8601 string), or None
        server_dt: Server's datetime (may be naive or aware)
        
    Returns:
        True if client change is newer and should be applied.
        Returns True if client_ts is None (no timestamp = always apply).
    """
    if not client_ts:
        return True  # No timestamp means always apply
    
    try:
        # Parse client timestamp to UTC
        client_dt = parse_iso_timestamp(client_ts)
        
        # Normalize server datetime to UTC
        if server_dt.tzinfo is None:
            # Naive datetime - assume it's already UTC (per our standard)
            server_utc = server_dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            server_utc = server_dt.astimezone(timezone.utc)
        
        debug(
            f"Timestamp comparison: client={client_dt.isoformat()}, server={server_utc.isoformat()}"
        )
        
        return client_dt >= server_utc
        
    except (ValueError, AttributeError) as e:
        debug(f"Timestamp comparison failed: {e}")
        return True  # Default to applying on parse error


def to_iso_string(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO 8601 string in UTC.
    
    Args:
        dt: Datetime to convert (may be None)
        
    Returns:
        ISO 8601 string with timezone, or None if dt is None
    """
    if dt is None:
        return None
    
    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC and format
    return dt.astimezone(timezone.utc).isoformat()
