"""SQLite storage for web assistant sessions, history, rate-limit, leads."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

WEB_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS web_sessions (
    session_id TEXT PRIMARY KEY,
    host TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS web_chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_chat_history_session
    ON web_chat_history (session_id, id);

CREATE TABLE IF NOT EXISTS web_rate_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate_key TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_rate_log_key
    ON web_rate_log (rate_key, kind, created_at);

CREATE TABLE IF NOT EXISTS web_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL DEFAULT '',
    host TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    need TEXT NOT NULL DEFAULT '',
    budget TEXT NOT NULL DEFAULT '',
    urgency TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    client_ip TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    extra_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_leads_created
    ON web_leads (created_at);
"""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


class WebStore:
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    async def init(self) -> None:
        await self._db.executescript(WEB_SCHEMA_SQL)
        await self._db.commit()

    async def touch_session(self, session_id: str, *, host: str, path: str) -> None:
        now = _isoformat(_utcnow())
        await self._db.execute(
            """
            INSERT INTO web_sessions (session_id, host, path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                host = excluded.host,
                path = excluded.path,
                updated_at = excluded.updated_at
            """,
            (session_id, host or "", path or "", now, now),
        )
        await self._db.commit()

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        text = (content or "").strip()
        if not text or role not in {"user", "assistant", "system"}:
            return
        await self._db.execute(
            """
            INSERT INTO web_chat_history (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, text, _isoformat(_utcnow())),
        )
        await self._db.commit()

    async def get_recent_messages(
        self,
        session_id: str,
        *,
        max_messages: int,
        ttl_hours: int,
    ) -> list[dict[str, str]]:
        if max_messages <= 0:
            return []
        cutoff = _isoformat(_utcnow() - timedelta(hours=ttl_hours))
        cursor = await self._db.execute(
            """
            SELECT role, content FROM web_chat_history
            WHERE session_id = ? AND created_at >= ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, cutoff, max_messages),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    async def trim_history(
        self,
        session_id: str,
        *,
        max_messages: int,
        ttl_hours: int,
    ) -> None:
        cutoff = _isoformat(_utcnow() - timedelta(hours=ttl_hours))
        await self._db.execute(
            "DELETE FROM web_chat_history WHERE session_id = ? AND created_at < ?",
            (session_id, cutoff),
        )
        if max_messages > 0:
            cursor = await self._db.execute(
                """
                SELECT id FROM web_chat_history
                WHERE session_id = ?
                ORDER BY id DESC
                """,
                (session_id,),
            )
            all_ids = [row[0] for row in await cursor.fetchall()]
            await cursor.close()
            old_ids = all_ids[max_messages:]
            if old_ids:
                placeholders = ",".join("?" * len(old_ids))
                await self._db.execute(
                    f"DELETE FROM web_chat_history WHERE id IN ({placeholders})",
                    old_ids,
                )
        await self._db.commit()

    async def is_rate_limited(
        self,
        rate_key: str,
        *,
        kind: str,
        limit_per_hour: int,
    ) -> bool:
        if limit_per_hour <= 0:
            return False
        since = _isoformat(_utcnow() - timedelta(hours=1))
        cursor = await self._db.execute(
            """
            SELECT COUNT(*) FROM web_rate_log
            WHERE rate_key = ? AND kind = ? AND created_at >= ?
            """,
            (rate_key, kind, since),
        )
        row = await cursor.fetchone()
        await cursor.close()
        count = int(row[0]) if row else 0
        return count >= limit_per_hour

    async def record_rate(self, rate_key: str, *, kind: str) -> None:
        await self._db.execute(
            "INSERT INTO web_rate_log (rate_key, kind, created_at) VALUES (?, ?, ?)",
            (rate_key, kind, _isoformat(_utcnow())),
        )
        await self._db.commit()

    async def save_lead(
        self,
        *,
        session_id: str,
        host: str,
        path: str,
        topic: str,
        need: str,
        budget: str,
        urgency: str,
        contact: str,
        client_ip: str,
        user_agent: str,
        extra: dict[str, Any] | None = None,
    ) -> int:
        now = _isoformat(_utcnow())
        cursor = await self._db.execute(
            """
            INSERT INTO web_leads (
                session_id, host, path, topic, need, budget, urgency, contact,
                client_ip, user_agent, extra_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                host,
                path,
                topic,
                need,
                budget,
                urgency,
                contact,
                client_ip,
                user_agent[:500],
                json.dumps(extra or {}, ensure_ascii=False),
                now,
            ),
        )
        await self._db.commit()
        return int(cursor.lastrowid or 0)
