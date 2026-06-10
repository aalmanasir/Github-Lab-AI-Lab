"""Simple schema versioning for the database."""

from __future__ import annotations

import logging

import aiosqlite

__all__ = ["check_schema_version", "CURRENT_SCHEMA_VERSION"]

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1

CREATE_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS _schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


async def check_schema_version(db: aiosqlite.Connection) -> int:
    """Check and record schema version. Returns current version."""
    await db.executescript(CREATE_VERSION_TABLE)

    cursor = await db.execute("SELECT MAX(version) as v FROM _schema_version")
    row = await cursor.fetchone()
    current = row[0] if row and row[0] is not None else 0

    if current < CURRENT_SCHEMA_VERSION:
        await db.execute(
            "INSERT INTO _schema_version (version) VALUES (?)",
            (CURRENT_SCHEMA_VERSION,),
        )
        await db.commit()
        logger.info("Schema version set to %d (was %d)", CURRENT_SCHEMA_VERSION, current)
    else:
        logger.info("Schema version: %d (current)", current)

    return CURRENT_SCHEMA_VERSION
