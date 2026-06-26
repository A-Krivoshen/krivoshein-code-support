from __future__ import annotations

import logging
from datetime import UTC, datetime

import aiosqlite

from app.bot.states import TicketState
from app.tickets.models import TicketSession
from app.tickets.serialization import deserialize_draft, serialize_draft

logger = logging.getLogger(__name__)


class TicketStorage:
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    async def get_session(self, chat_id: int) -> TicketSession | None:
        cursor = await self._db.execute(
            """
            SELECT chat_id, state, topic, description, contact, urgency, draft_json
            FROM ticket_sessions
            WHERE chat_id = ?
            """,
            (chat_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None

        draft_json = row[6] if len(row) > 6 and row[6] else "{}"
        return TicketSession(
            chat_id=row[0],
            state=TicketState(row[1]),
            draft=deserialize_draft(
                draft_json,
                topic=row[2] or "",
                description=row[3] or "",
                contact=row[4] or "",
                urgency=row[5] or "",
            ),
        )

    async def save_session(self, session: TicketSession) -> None:
        draft_json = serialize_draft(session.draft)
        try:
            await self._db.execute(
                """
                INSERT INTO ticket_sessions (
                    chat_id, state, topic, description, contact, urgency, draft_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    state = excluded.state,
                    draft_json = excluded.draft_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session.chat_id,
                    session.state.value,
                    session.draft.topic,
                    session.draft.description,
                    session.draft.contact,
                    session.draft.urgency,
                    draft_json,
                    datetime.now(UTC).isoformat(),
                ),
            )
            await self._db.commit()
        except aiosqlite.Error:
            logger.exception("Не удалось сохранить сессию chat_id=%s", session.chat_id)
            raise

    async def delete_session(self, chat_id: int) -> None:
        try:
            await self._db.execute("DELETE FROM ticket_sessions WHERE chat_id = ?", (chat_id,))
            await self._db.commit()
        except aiosqlite.Error:
            logger.exception("Не удалось удалить сессию chat_id=%s", chat_id)
            raise

    async def has_active_ticket_flow(self, chat_id: int) -> bool:
        cursor = await self._db.execute(
            """
            SELECT 1
            FROM ticket_sessions
            WHERE chat_id = ? AND state != ?
            LIMIT 1
            """,
            (chat_id, TicketState.IDLE.value),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return row is not None