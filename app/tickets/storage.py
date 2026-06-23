from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite

from app.bot.states import TicketState
from app.tickets.models import TicketDraft, TicketSession


class TicketStorage:
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    async def get_draft(self, chat_id: int) -> TicketDraft | None:
        cursor = await self._db.execute(
            """
            SELECT topic, description, contact, urgency
            FROM ticket_sessions
            WHERE chat_id = ?
            """,
            (chat_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return TicketDraft(topic=row[0], description=row[1], contact=row[2], urgency=row[3])

    async def save_draft(self, chat_id: int, draft: TicketDraft) -> None:
        session = await self.get_session(chat_id)
        if session is None:
            session = TicketSession(chat_id=chat_id, draft=draft)
        else:
            session.draft = draft
        await self.save_session(session)

    async def delete_draft(self, chat_id: int) -> None:
        await self.delete_session(chat_id)

    async def get_session(self, chat_id: int) -> TicketSession | None:
        cursor = await self._db.execute(
            """
            SELECT chat_id, state, topic, description, contact, urgency
            FROM ticket_sessions
            WHERE chat_id = ?
            """,
            (chat_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None

        return TicketSession(
            chat_id=row[0],
            state=TicketState(row[1]),
            draft=TicketDraft(topic=row[2], description=row[3], contact=row[4], urgency=row[5]),
        )

    async def save_session(self, session: TicketSession) -> None:
        await self._db.execute(
            """
            INSERT INTO ticket_sessions (
                chat_id, state, topic, description, contact, urgency, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                state = excluded.state,
                topic = excluded.topic,
                description = excluded.description,
                contact = excluded.contact,
                urgency = excluded.urgency,
                updated_at = excluded.updated_at
            """,
            (
                session.chat_id,
                session.state.value,
                session.draft.topic,
                session.draft.description,
                session.draft.contact,
                session.draft.urgency,
                datetime.now(UTC).isoformat(),
            ),
        )
        await self._db.commit()

    async def delete_session(self, chat_id: int) -> None:
        await self._db.execute("DELETE FROM ticket_sessions WHERE chat_id = ?", (chat_id,))
        await self._db.commit()

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