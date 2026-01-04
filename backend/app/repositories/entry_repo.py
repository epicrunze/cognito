"""
Entry repository for database operations.

Handles all Entry CRUD operations using DuckDB.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import duckdb

from app.models.entry import EntryCreate, EntryInDB, EntryUpdate, EntryVersion
from app.utils.timestamp import utc_now


def get_entries(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    status: Optional[str] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "date:desc",
) -> tuple[list[EntryInDB], int]:
    """
    Get entries with optional filtering.

    Args:
        conn: DuckDB connection
        user_id: User ID to filter by
        status: Filter by status (active/archived)
        after_date: Filter entries after this date (YYYY-MM-DD)
        before_date: Filter entries before this date (YYYY-MM-DD)
        limit: Maximum number of entries to return
        offset: Number of entries to skip
        order_by: Order by field:direction (e.g., "date:desc")

    Returns:
        Tuple of (entries list, total count)
    """
    # Build WHERE clause
    where_clauses = ["user_id = ?"]
    params = [str(user_id)]

    if status:
        where_clauses.append("status = ?")
        params.append(status)

    if after_date:
        where_clauses.append("date > ?")
        params.append(after_date)

    if before_date:
        where_clauses.append("date < ?")
        params.append(before_date)

    where_sql = " AND ".join(where_clauses)

    # Parse order_by
    if ":" in order_by:
        field, direction = order_by.split(":")
        direction = direction.upper()
    else:
        field = order_by
        direction = "DESC"

    # Get total count
    count_query = f"SELECT COUNT(*) FROM entries WHERE {where_sql}"
    total = conn.execute(count_query, params).fetchone()[0]

    # Get entries
    query = f"""
        SELECT 
            id, user_id, date, conversations, refined_output,
            relevance_score, last_interacted_at, interaction_count,
            status, pending_refine, refine_status, refine_error,
            version, created_at, updated_at
        FROM entries
        WHERE {where_sql}
        ORDER BY {field} {direction}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    results = conn.execute(query, params).fetchall()

    entries = []
    for row in results:
        # Parse JSON conversations
        conversations = json.loads(row[3]) if row[3] else []

        # Handle UUID - DuckDB may return UUID objects or strings
        entry_id = row[0] if isinstance(row[0], UUID) else UUID(row[0])
        user_id = row[1] if isinstance(row[1], UUID) else UUID(row[1])

        entry = EntryInDB(
            id=entry_id,
            user_id=user_id,
            date=str(row[2]),
            conversations=conversations,
            refined_output=row[4] or "",
            relevance_score=row[5],
            last_interacted_at=row[6],
            interaction_count=row[7],
            status=row[8],
            pending_refine=row[9] or False,
            refine_status=row[10] or "idle",
            refine_error=row[11],
            version=row[12],
            created_at=row[13],
            updated_at=row[14],
        )
        entries.append(entry)

    return entries, total


def get_entry_by_id(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    user_id: UUID,
) -> Optional[EntryInDB]:
    """
    Get a single entry by ID.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        user_id: User ID for ownership check

    Returns:
        Entry if found and owned by user, None otherwise
    """
    query = """
        SELECT 
            id, user_id, date, conversations, refined_output,
            relevance_score, last_interacted_at, interaction_count,
            status, pending_refine, refine_status, refine_error,
            version, created_at, updated_at
        FROM entries
        WHERE id = ? AND user_id = ?
    """

    result = conn.execute(query, [str(entry_id), str(user_id)]).fetchone()

    if not result:
        return None

    # Parse JSON conversations
    conversations = json.loads(result[3]) if result[3] else []

    # Handle UUID - DuckDB may return UUID objects or strings
    entry_id = result[0] if isinstance(result[0], UUID) else UUID(result[0])
    user_id = result[1] if isinstance(result[1], UUID) else UUID(result[1])

    return EntryInDB(
        id=entry_id,
        user_id=user_id,
        date=str(result[2]),
        conversations=conversations,
        refined_output=result[4] or "",
        relevance_score=result[5],
        last_interacted_at=result[6],
        interaction_count=result[7],
        status=result[8],
        pending_refine=result[9] or False,
        refine_status=result[10] or "idle",
        refine_error=result[11],
        version=result[12],
        created_at=result[13],
        updated_at=result[14],
    )


def get_entry_by_date(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    date: str,
) -> Optional[EntryInDB]:
    """
    Get entry by date.

    Args:
        conn: DuckDB connection
        user_id: User ID
        date: Entry date (YYYY-MM-DD)

    Returns:
        Entry if found, None otherwise
    """
    query = """
        SELECT 
            id, user_id, date, conversations, refined_output,
            relevance_score, last_interacted_at, interaction_count,
            status, pending_refine, refine_status, refine_error,
            version, created_at, updated_at
        FROM entries
        WHERE user_id = ? AND date = ?
    """

    result = conn.execute(query, [str(user_id), date]).fetchone()

    if not result:
        return None

    # Parse JSON conversations
    conversations = json.loads(result[3]) if result[3] else []

    # Handle UUID - DuckDB may return UUID objects or strings
    entry_id = result[0] if isinstance(result[0], UUID) else UUID(result[0])
    user_id = result[1] if isinstance(result[1], UUID) else UUID(result[1])

    return EntryInDB(
        id=entry_id,
        user_id=user_id,
        date=str(result[2]),
        conversations=conversations,
        refined_output=result[4] or "",
        relevance_score=result[5],
        last_interacted_at=result[6],
        interaction_count=result[7],
        status=result[8],
        pending_refine=result[9] or False,
        refine_status=result[10] or "idle",
        refine_error=result[11],
        version=result[12],
        created_at=result[13],
        updated_at=result[14],
    )


def create_entry(
    conn: duckdb.DuckDBPyConnection,
    entry_data: EntryCreate,
    user_id: UUID,
    entry_id: Optional[UUID] = None,
) -> EntryInDB:
    """
    Create a new entry.

    Args:
        conn: DuckDB connection
        entry_data: Entry creation data
        user_id: User ID
        entry_id: Optional entry ID (for sync with client-generated UUIDs)

    Returns:
        Created entry
    """
    if entry_id is None:
        entry_id = uuid4()
    now = utc_now()

    # Convert conversations to JSON
    conversations_json = json.dumps(
        [conv.model_dump(mode="json") for conv in entry_data.conversations]
    )

    query = """
        INSERT INTO entries (
            id, user_id, date, conversations, refined_output,
            relevance_score, last_interacted_at, interaction_count,
            status, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    conn.execute(
        query,
        [
            str(entry_id),
            str(user_id),
            entry_data.date,
            conversations_json,
            entry_data.refined_output,
            1.0,  # Default relevance_score
            now,
            0,  # Default interaction_count
            "active",  # Default status
            1,  # Default version
            now,
            now,
        ],
    )

    return EntryInDB(
        id=entry_id,
        user_id=user_id,
        date=entry_data.date,
        conversations=entry_data.conversations,
        refined_output=entry_data.refined_output,
        relevance_score=1.0,
        last_interacted_at=now,
        interaction_count=0,
        status="active",
        version=1,
        created_at=now,
        updated_at=now,
    )


def update_entry(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    user_id: UUID,
    entry_data: EntryUpdate,
) -> Optional[EntryInDB]:
    """
    Update an entry.

    Creates a version snapshot before updating.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        user_id: User ID for ownership check
        entry_data: Update data

    Returns:
        Updated entry if found and owned by user, None otherwise
    """
    # Get current entry
    current_entry = get_entry_by_id(conn, entry_id, user_id)
    if not current_entry:
        return None

    # Create version snapshot
    create_entry_version(
        conn,
        entry_id,
        current_entry.version,
        current_entry.refined_output,
    )

    # Build update query
    update_fields = []
    params = []

    if entry_data.conversations is not None:
        conversations_json = json.dumps(
            [conv.model_dump(mode="json") for conv in entry_data.conversations]
        )
        update_fields.append("conversations = ?")
        params.append(conversations_json)

    if entry_data.refined_output is not None:
        update_fields.append("refined_output = ?")
        params.append(entry_data.refined_output)

    if entry_data.relevance_score is not None:
        update_fields.append("relevance_score = ?")
        params.append(entry_data.relevance_score)

    if entry_data.status is not None:
        update_fields.append("status = ?")
        params.append(entry_data.status)

    if entry_data.pending_refine is not None:
        update_fields.append("pending_refine = ?")
        params.append(entry_data.pending_refine)

    if entry_data.refine_status is not None:
        update_fields.append("refine_status = ?")
        params.append(entry_data.refine_status)

    if entry_data.refine_error is not None:
        update_fields.append("refine_error = ?")
        params.append(entry_data.refine_error)

    # Always increment version and update timestamp
    update_fields.append("version = version + 1")
    update_fields.append("updated_at = ?")
    params.append(utc_now())

    # Add WHERE clause params
    params.extend([str(entry_id), str(user_id)])

    query = f"""
        UPDATE entries
        SET {", ".join(update_fields)}
        WHERE id = ? AND user_id = ?
    """

    conn.execute(query, params)

    # Return updated entry
    return get_entry_by_id(conn, entry_id, user_id)


def update_last_interacted_at(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
) -> None:
    """
    Update last_interacted_at timestamp and increment interaction_count.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
    """
    query = """
        UPDATE entries
        SET 
            last_interacted_at = ?,
            interaction_count = interaction_count + 1
        WHERE id = ?
    """

    conn.execute(query, [utc_now(), str(entry_id)])


def get_entry_versions(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    user_id: UUID,
) -> list[EntryVersion]:
    """
    Get version history for an entry.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        user_id: User ID for ownership check

    Returns:
        List of entry versions
    """
    # First verify ownership
    entry = get_entry_by_id(conn, entry_id, user_id)
    if not entry:
        return []

    query = """
        SELECT id, entry_id, version, content_snapshot, created_at
        FROM entry_versions
        WHERE entry_id = ?
        ORDER BY version DESC
    """

    results = conn.execute(query, [str(entry_id)]).fetchall()

    versions = []
    for row in results:
        # Handle UUID - DuckDB may return UUID objects or strings
        version_id = row[0] if isinstance(row[0], UUID) else UUID(row[0])
        entry_id = row[1] if isinstance(row[1], UUID) else UUID(row[1])

        version = EntryVersion(
            id=version_id,
            entry_id=entry_id,
            version=row[2],
            content_snapshot=row[3],
            created_at=row[4],
        )
        versions.append(version)

    return versions


def create_entry_version(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    version: int,
    content_snapshot: str,
) -> None:
    """
    Create a version snapshot.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        version: Version number
        content_snapshot: Content at this version
    """
    version_id = uuid4()

    query = """
        INSERT INTO entry_versions (id, entry_id, version, content_snapshot, created_at)
        VALUES (?, ?, ?, ?, ?)
    """

    conn.execute(
        query,
        [
            str(version_id),
            str(entry_id),
            version,
            content_snapshot,
            utc_now(),
        ],
    )


def get_entries_since(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    since: Optional[datetime] = None,
) -> list[EntryInDB]:
    """
    Get entries modified since a given timestamp.

    Args:
        conn: DuckDB connection
        user_id: User ID
        since: Get entries updated after this timestamp (None for all)

    Returns:
        List of entries
    """
    if since:
        query = """
            SELECT 
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, pending_refine, refine_status, refine_error,
                version, created_at, updated_at
            FROM entries
            WHERE user_id = ? AND updated_at > ?
            ORDER BY updated_at DESC
        """
        results = conn.execute(query, [str(user_id), since]).fetchall()
    else:
        query = """
            SELECT 
                id, user_id, date, conversations, refined_output,
                relevance_score, last_interacted_at, interaction_count,
                status, pending_refine, refine_status, refine_error,
                version, created_at, updated_at
            FROM entries
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """
        results = conn.execute(query, [str(user_id)]).fetchall()

    entries = []
    for row in results:
        conversations = json.loads(row[3]) if row[3] else []
        entry_id = row[0] if isinstance(row[0], UUID) else UUID(row[0])
        uid = row[1] if isinstance(row[1], UUID) else UUID(row[1])

        entries.append(EntryInDB(
            id=entry_id,
            user_id=uid,
            date=str(row[2]),
            conversations=conversations,
            refined_output=row[4] or "",
            relevance_score=row[5],
            last_interacted_at=row[6],
            interaction_count=row[7],
            status=row[8],
            pending_refine=row[9] or False,
            refine_status=row[10] or "idle",
            refine_error=row[11],
            version=row[12],
            created_at=row[13],
            updated_at=row[14],
        ))

    return entries


def list_entries(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    status: str = "active",
) -> list[EntryInDB]:
    """
    List all entries for a user with optional status filter.

    Args:
        conn: DuckDB connection
        user_id: User ID
        status: Filter by status (default: active)

    Returns:
        List of entries
    """
    query = """
        SELECT 
            id, user_id, date, conversations, refined_output,
            relevance_score, last_interacted_at, interaction_count,
            status, pending_refine, refine_status, refine_error,
            version, created_at, updated_at
        FROM entries
        WHERE user_id = ? AND status = ?
        ORDER BY date DESC
    """
    results = conn.execute(query, [str(user_id), status]).fetchall()

    entries = []
    for row in results:
        conversations = json.loads(row[3]) if row[3] else []
        entry_id = row[0] if isinstance(row[0], UUID) else UUID(row[0])
        uid = row[1] if isinstance(row[1], UUID) else UUID(row[1])

        entries.append(EntryInDB(
            id=entry_id,
            user_id=uid,
            date=str(row[2]),
            conversations=conversations,
            refined_output=row[4] or "",
            relevance_score=row[5],
            last_interacted_at=row[6],
            interaction_count=row[7],
            status=row[8],
            pending_refine=row[9] or False,
            refine_status=row[10] or "idle",
            refine_error=row[11],
            version=row[12],
            created_at=row[13],
            updated_at=row[14],
        ))

    return entries


def get_entries_pending_refine(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    limit: int = 5,
) -> list[EntryInDB]:
    """
    Get entries queued for refinement.

    Args:
        conn: DuckDB connection
        user_id: User ID
        limit: Maximum number of entries to return

    Returns:
        List of entries with pending_refine=True
    """
    query = """
        SELECT 
            id, user_id, date, conversations, refined_output,
            relevance_score, last_interacted_at, interaction_count,
            status, pending_refine, refine_status, refine_error,
            version, created_at, updated_at
        FROM entries
        WHERE user_id = ? AND pending_refine = TRUE AND refine_status != 'processing'
        ORDER BY updated_at ASC
        LIMIT ?
    """
    results = conn.execute(query, [str(user_id), limit]).fetchall()

    entries = []
    for row in results:
        conversations = json.loads(row[3]) if row[3] else []
        entry_id = row[0] if isinstance(row[0], UUID) else UUID(row[0])
        uid = row[1] if isinstance(row[1], UUID) else UUID(row[1])

        entries.append(EntryInDB(
            id=entry_id,
            user_id=uid,
            date=str(row[2]),
            conversations=conversations,
            refined_output=row[4] or "",
            relevance_score=row[5],
            last_interacted_at=row[6],
            interaction_count=row[7],
            status=row[8],
            pending_refine=row[9] or False,
            refine_status=row[10] or "idle",
            refine_error=row[11],
            version=row[12],
            created_at=row[13],
            updated_at=row[14],
        ))

    return entries


def update_entry_refine_status(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    user_id: UUID,
    status: str,
    error: Optional[str] = None,
) -> None:
    """
    Update the refine status of an entry.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        user_id: User ID for ownership check
        status: New refine status
        error: Optional error message
    """
    query = """
        UPDATE entries
        SET refine_status = ?, refine_error = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
    """
    conn.execute(query, [status, error, utc_now(), str(entry_id), str(user_id)])


def clear_pending_refine(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    user_id: UUID,
) -> None:
    """
    Clear the pending_refine flag for an entry.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        user_id: User ID for ownership check
    """
    query = """
        UPDATE entries
        SET pending_refine = FALSE, updated_at = ?
        WHERE id = ? AND user_id = ?
    """
    conn.execute(query, [utc_now(), str(entry_id), str(user_id)])


def set_pending_refine(
    conn: duckdb.DuckDBPyConnection,
    entry_id: UUID,
    user_id: UUID,
) -> bool:
    """
    Set the pending_refine flag for an entry.

    Only sets if not already pending or processing.

    Args:
        conn: DuckDB connection
        entry_id: Entry ID
        user_id: User ID for ownership check

    Returns:
        True if flag was set, False if already pending/processing
    """
    # Check current status
    check_query = """
        SELECT pending_refine, refine_status 
        FROM entries 
        WHERE id = ? AND user_id = ?
    """
    result = conn.execute(check_query, [str(entry_id), str(user_id)]).fetchone()
    
    if not result:
        return False
    
    pending_refine, refine_status = result
    
    # Don't double-queue
    if pending_refine or refine_status == "processing":
        return False
    
    # Set pending_refine flag
    query = """
        UPDATE entries
        SET pending_refine = TRUE, refine_status = 'idle', refine_error = NULL, updated_at = ?
        WHERE id = ? AND user_id = ?
    """
    conn.execute(query, [utc_now(), str(entry_id), str(user_id)])
    return True


