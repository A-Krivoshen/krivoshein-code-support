from __future__ import annotations

from pathlib import Path

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ticket_sessions (
    chat_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    urgency TEXT NOT NULL DEFAULT '',
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


async def _ensure_urgency_column(connection: aiosqlite.Connection) -> None:
    cursor = await connection.execute("PRAGMA table_info(ticket_sessions)")
    columns = {row[1] for row in await cursor.fetchall()}
    await cursor.close()
    if "urgency" not in columns:
        await connection.execute(
            "ALTER TABLE ticket_sessions ADD COLUMN urgency TEXT NOT NULL DEFAULT ''"
        )
        await connection.commit()