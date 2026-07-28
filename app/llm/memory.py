from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


class ChatMemory:
    """SQLite: rate-limit LLM-запросов + короткая история idle-диалога."""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    # --- Rate limit ---------------------------------------------------------

    async def count_requests_since(self, chat_id: int, since: datetime) -> int:
        cursor = await self._db.execute(
            """
            SELECT COUNT(*) FROM llm_request_log
            WHERE chat_id = ? AND created_at >= ?
            """,
            (chat_id, _isoformat(since)),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return int(row[0]) if row else 0

    async def is_rate_limited(self, chat_id: int, *, limit_per_hour: int) -> bool:
        if limit_per_hour <= 0:
            return False
        since = _utcnow() - timedelta(hours=1)
        count = await self.count_requests_since(chat_id, since)
        return count >= limit_per_hour

    async def record_request(self, chat_id: int) -> None:
        now = _isoformat(_utcnow())
        try:
            await self._db.execute(
                "INSERT INTO llm_request_log (chat_id, created_at) VALUES (?, ?)",
                (chat_id, now),
            )
            await self._db.commit()
        except aiosqlite.Error:
            logger.exception("Не удалось записать llm_request_log chat_id=%s", chat_id)
            raise

    async def prune_request_log(self, *, older_than_hours: int = 48) -> int:
        cutoff = _isoformat(_utcnow() - timedelta(hours=older_than_hours))
        cursor = await self._db.execute(
            "DELETE FROM llm_request_log WHERE created_at < ?",
            (cutoff,),
        )
        await self._db.commit()
        deleted = cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else 0
        await cursor.close()
        return deleted

    # --- History ------------------------------------------------------------

    async def append_message(self, chat_id: int, role: str, content: str) -> None:
        text = (content or "").strip()
        if not text or role not in {"user", "assistant", "system"}:
            return
        try:
            await self._db.execute(
                """
                INSERT INTO chat_history (chat_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, role, text, _isoformat(_utcnow())),
            )
            await self._db.commit()
        except aiosqlite.Error:
            logger.exception("Не удалось сохранить chat_history chat_id=%s", chat_id)
            raise

    async def get_recent_messages(
        self,
        chat_id: int,
        *,
        max_messages: int,
        ttl_hours: int,
    ) -> list[dict[str, str]]:
        """Последние сообщения (старые → новые), с учётом TTL."""
        if max_messages <= 0:
            return []

        cutoff = _isoformat(_utcnow() - timedelta(hours=ttl_hours))
        # Берём с запасом, потом обрежем
        cursor = await self._db.execute(
            """
            SELECT role, content FROM chat_history
            WHERE chat_id = ? AND created_at >= ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, cutoff, max_messages),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
        return messages

    async def get_recent_user_texts(
        self,
        chat_id: int,
        *,
        limit: int = 3,
        ttl_hours: int = 24,
    ) -> list[str]:
        cutoff = _isoformat(_utcnow() - timedelta(hours=ttl_hours))
        cursor = await self._db.execute(
            """
            SELECT content FROM chat_history
            WHERE chat_id = ? AND role = 'user' AND created_at >= ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, cutoff, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [row[0] for row in rows if row[0]]

    async def trim_history(
        self,
        chat_id: int,
        *,
        max_messages: int,
        ttl_hours: int,
    ) -> None:
        """Удаляет просроченные и лишние сообщения сверх max_messages."""
        cutoff = _isoformat(_utcnow() - timedelta(hours=ttl_hours))
        await self._db.execute(
            "DELETE FROM chat_history WHERE chat_id = ? AND created_at < ?",
            (chat_id, cutoff),
        )

        if max_messages > 0:
            cursor = await self._db.execute(
                """
                SELECT id FROM chat_history
                WHERE chat_id = ?
                ORDER BY id DESC
                """,
                (chat_id,),
            )
            all_ids = [row[0] for row in await cursor.fetchall()]
            await cursor.close()
            old_ids = all_ids[max_messages:]
            if old_ids:
                placeholders = ",".join("?" * len(old_ids))
                await self._db.execute(
                    f"DELETE FROM chat_history WHERE id IN ({placeholders})",
                    old_ids,
                )

        await self._db.commit()

    async def clear_history(self, chat_id: int) -> None:
        try:
            await self._db.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))
            await self._db.commit()
        except aiosqlite.Error:
            logger.exception("Не удалось очистить chat_history chat_id=%s", chat_id)
            raise

    async def has_recent_history(self, chat_id: int, *, ttl_hours: int = 24) -> bool:
        cutoff = _isoformat(_utcnow() - timedelta(hours=ttl_hours))
        cursor = await self._db.execute(
            """
            SELECT 1 FROM chat_history
            WHERE chat_id = ? AND created_at >= ?
            LIMIT 1
            """,
            (chat_id, cutoff),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return row is not None
