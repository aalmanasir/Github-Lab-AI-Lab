"""Async SQLite database setup and query functions."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from clowdbot.config import get_settings

__all__ = [
    "init_db",
    "get_db",
    "log_event",
    "log_command",
    "log_webhook",
    "log_uptime",
    "get_events",
    "get_recent_events",
    "get_event_by_id",
    "get_event_stats",
    "search_events",
    "check_db_health",
    "create_incident",
    "get_incident",
    "list_incidents",
    "update_incident",
    "resolve_incident",
    "get_incident_stats",
]

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    summary TEXT NOT NULL,
    detail TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT,
    username TEXT,
    command TEXT NOT NULL,
    args TEXT,
    channel TEXT,
    response TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    delivery_id TEXT,
    payload TEXT,
    processed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uptime_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    response_time_ms REAL,
    endpoint TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_log_timestamp ON event_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_log_source ON event_log(source);
CREATE INDEX IF NOT EXISTS idx_event_log_severity ON event_log(severity);
CREATE INDEX IF NOT EXISTS idx_event_log_event_type ON event_log(event_type);
CREATE INDEX IF NOT EXISTS idx_event_log_source_severity ON event_log(source, severity, timestamp);
CREATE INDEX IF NOT EXISTS idx_webhook_log_provider ON webhook_log(provider);
CREATE INDEX IF NOT EXISTS idx_uptime_log_timestamp ON uptime_log(timestamp);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    incident_type TEXT NOT NULL DEFAULT 'unknown',
    severity TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open',
    assigned_to TEXT,
    classification TEXT,
    recommendation TEXT,
    resolution TEXT,
    resolved_at TEXT,
    resolved_by TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp);
CREATE INDEX IF NOT EXISTS idx_incidents_status_severity ON incidents(status, severity, timestamp);
"""


def _now() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


async def init_db() -> None:
    """Initialize the database connection and create tables."""
    global _db
    settings = get_settings()
    db_path = settings.db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing database at %s", db_path)
    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(CREATE_TABLES_SQL)
    await _db.commit()

    # Track schema version
    from clowdbot.database_migrations import check_schema_version
    await check_schema_version(_db)

    logger.info("Database initialized successfully")


async def get_db() -> aiosqlite.Connection:
    """Get the active database connection."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


async def log_event(
    source: str,
    event_type: str,
    summary: str,
    severity: str = "info",
    detail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    """Log an event to the event_log table. Returns the event ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO event_log (timestamp, source, event_type, severity, summary, detail, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (_now(), source, event_type, severity, summary, detail, json.dumps(metadata) if metadata else None),
    )
    await db.commit()
    event_id = cursor.lastrowid
    logger.info("Logged event #%d: [%s] %s - %s", event_id, severity, source, summary)
    return event_id  # type: ignore[return-value]


async def log_command(
    user_id: str,
    username: str,
    command: str,
    args: str | None = None,
    channel: str | None = None,
    response: str | None = None,
) -> int:
    """Log a command execution to command_log. Returns the record ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO command_log (timestamp, user_id, username, command, args, channel, response)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (_now(), user_id, username, command, args, channel, response),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore[return-value]


async def log_webhook(
    provider: str,
    event_type: str,
    delivery_id: str | None = None,
    payload: str | None = None,
    processed: bool = False,
) -> int:
    """Log a webhook delivery to webhook_log. Returns the record ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO webhook_log (timestamp, provider, event_type, delivery_id, payload, processed)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (_now(), provider, event_type, delivery_id, payload, 1 if processed else 0),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore[return-value]


async def log_uptime(
    status: str,
    response_time_ms: float | None = None,
    endpoint: str | None = None,
) -> int:
    """Log an uptime check result. Returns the record ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO uptime_log (timestamp, status, response_time_ms, endpoint)
           VALUES (?, ?, ?, ?)""",
        (_now(), status, response_time_ms, endpoint),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore[return-value]


async def get_events(
    source: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Get events with optional filters. Returns list of event dicts."""
    db = await get_db()
    conditions: list[str] = []
    params: list[Any] = []

    if source:
        conditions.append("source = ?")
        params.append(source)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if since:
        conditions.append("timestamp >= ?")
        params.append(since)
    if until:
        conditions.append("timestamp <= ?")
        params.append(until)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM event_log {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_recent_events(limit: int = 10) -> list[dict[str, Any]]:
    """Get the most recent events."""
    return await get_events(limit=limit)


async def get_event_by_id(event_id: int) -> dict[str, Any] | None:
    """Get a single event by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM event_log WHERE id = ?", (event_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_event_stats() -> dict[str, Any]:
    """Get aggregate event statistics."""
    db = await get_db()

    # Fetch total count and last-24h count in a single query
    summary_cursor = await db.execute(
        """SELECT
               COUNT(*) as total,
               SUM(CASE WHEN timestamp >= datetime('now', '-24 hours') THEN 1 ELSE 0 END) as last_24h
           FROM event_log"""
    )
    summary_row = await summary_cursor.fetchone()
    total = summary_row["total"] if summary_row else 0
    last_24h = summary_row["last_24h"] if summary_row else 0

    severity_cursor = await db.execute(
        "SELECT severity, COUNT(*) as count FROM event_log GROUP BY severity"
    )
    severity_rows = await severity_cursor.fetchall()
    by_severity = {row["severity"]: row["count"] for row in severity_rows}

    source_cursor = await db.execute(
        "SELECT source, COUNT(*) as count FROM event_log GROUP BY source ORDER BY count DESC LIMIT 10"
    )
    source_rows = await source_cursor.fetchall()
    by_source = {row["source"]: row["count"] for row in source_rows}

    return {
        "total_events": total,
        "last_24h": last_24h,
        "by_severity": by_severity,
        "by_source": by_source,
    }


async def search_events(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search events by summary or detail content."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM event_log
           WHERE summary LIKE ? OR detail LIKE ?
           ORDER BY timestamp DESC LIMIT ?""",
        (f"%{query}%", f"%{query}%", limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def check_db_health() -> bool:
    """Check database connectivity."""
    try:
        db = await get_db()
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


# ---------------------------------------------------------------------------
# Incident CRUD
# ---------------------------------------------------------------------------


async def create_incident(
    title: str,
    description: str | None = None,
    source: str = "manual",
    incident_type: str = "unknown",
    severity: str = "medium",
    metadata: dict[str, Any] | None = None,
) -> int:
    """Create a new incident. Returns the incident ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO incidents (timestamp, title, description, source, incident_type, severity, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (_now(), title, description, source, incident_type, severity, json.dumps(metadata) if metadata else None),
    )
    await db.commit()
    incident_id = cursor.lastrowid
    logger.info("Created incident #%d: %s (%s/%s)", incident_id, title, incident_type, severity)
    return incident_id  # type: ignore[return-value]


async def get_incident(incident_id: int) -> dict[str, Any] | None:
    """Get a single incident by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def list_incidents(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List incidents with optional filters."""
    db = await get_db()
    conditions: list[str] = []
    params: list[Any] = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM incidents {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def update_incident(incident_id: int, **fields: Any) -> bool:
    """Update arbitrary fields on an incident. Returns True if a row was modified."""
    if not fields:
        return False
    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = [*fields.values(), incident_id]
    db = await get_db()
    cursor = await db.execute(
        f"UPDATE incidents SET {set_clause} WHERE id = ?",
        values,
    )
    await db.commit()
    return cursor.rowcount > 0


async def resolve_incident(incident_id: int, resolution: str, resolved_by: str) -> bool:
    """Resolve an incident. Returns True if successful."""
    now = _now()
    db = await get_db()
    cursor = await db.execute(
        """UPDATE incidents
           SET status = 'resolved', resolution = ?, resolved_by = ?, resolved_at = ?, updated_at = ?
           WHERE id = ? AND status != 'resolved'""",
        (resolution, resolved_by, now, now, incident_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_incident_stats() -> dict[str, Any]:
    """Get aggregate incident statistics."""
    db = await get_db()

    # Fetch total count and average resolution time in a single pass
    summary_cursor = await db.execute(
        """SELECT
               COUNT(*) as total,
               AVG(
                   CASE WHEN resolved_at IS NOT NULL
                        THEN (julianday(resolved_at) - julianday(timestamp)) * 86400
                   END
               ) as avg_seconds
           FROM incidents"""
    )
    summary_row = await summary_cursor.fetchone()
    total = summary_row["total"] if summary_row else 0
    avg_resolution_seconds = (
        round(summary_row["avg_seconds"], 1) if summary_row and summary_row["avg_seconds"] else None
    )

    status_cursor = await db.execute(
        "SELECT status, COUNT(*) as count FROM incidents GROUP BY status"
    )
    by_status = {row["status"]: row["count"] for row in await status_cursor.fetchall()}

    severity_cursor = await db.execute(
        "SELECT severity, COUNT(*) as count FROM incidents GROUP BY severity"
    )
    by_severity = {row["severity"]: row["count"] for row in await severity_cursor.fetchall()}

    return {
        "total_incidents": total,
        "by_status": by_status,
        "by_severity": by_severity,
        "avg_resolution_seconds": avg_resolution_seconds,
    }
