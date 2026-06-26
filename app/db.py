from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from app.tickets.serialization import deserialize_draft, serialize_draft

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ticket_sessions (
    chat_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    urgency TEXT NOT NULL DEFAULT '',
    draft_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);
"""


async def connect_db(database_path: str | Path) -> aiosqlite.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(path)
    await connection.execute("PRAGMA foreign_keys = ON")
    await connection.execute("PRAGMA busy_timeout = 5000")
    return connection


async def init_db(connection: aiosqlite.Connection) -> None:
    await connection.executescript(SCHEMA_SQL)
    await connection.commit()
    await _ensure_urgency_column(connection)
    await _ensure_draft_json_column(connection)
    await _migrate_legacy_drafts(connection)


async def _ensure_urgency_column(connection: aiosqlite.Connection) -> None:
    cursor = await connection.execute("PRAGMA table_info(ticket_sessions)")
    columns = {row[1] for row in await cursor.fetchall()}
    await cursor.close()
    if "urgency" not in columns:
        await connection.execute(
            "ALTER TABLE ticket_sessions ADD COLUMN urgency TEXT NOT NULL DEFAULT ''"
        )
        await connection.commit()


async def _ensure_draft_json_column(connection: aiosqlite.Connection) -> None:
    cursor = await connection.execute("PRAGMA table_info(ticket_sessions)")
    columns = {row[1] for row in await cursor.fetchall()}
    await cursor.close()
    if "draft_json" not in columns:
        await connection.execute(
            "ALTER TABLE ticket_sessions ADD COLUMN draft_json TEXT NOT NULL DEFAULT '{}'"
        )
        await connection.commit()


async def _migrate_legacy_drafts(connection: aiosqlite.Connection) -> None:
    cursor = await connection.execute(
        """
        SELECT chat_id, topic, description, contact, urgency, draft_json
        FROM ticket_sessions
        """
    )
    rows = await cursor.fetchall()
    await cursor.close()

    migrated = 0
    for row in rows:
        chat_id, topic, description, contact, urgency, draft_json = row
        draft = deserialize_draft(
            draft_json or "{}",
            topic=topic or "",
            description=description or "",
            contact=contact or "",
            urgency=urgency or "",
        )
        consolidated = serialize_draft(draft)
        if consolidated == (draft_json or "{}"):
            continue

        await connection.execute(
            "UPDATE ticket_sessions SET draft_json = ? WHERE chat_id = ?",
            (consolidated, chat_id),
        )
        migrated += 1

    if migrated:
        await connection.commit()
        logger.info("Мигрировано сессий заявок: %s", migrated)