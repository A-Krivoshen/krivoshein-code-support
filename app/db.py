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