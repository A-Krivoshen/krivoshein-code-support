from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from app.bot.states import TicketState
from app.tickets.models import TicketDraft, TicketMedia, TicketSession


def _int_from_value(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _ticket_media_from_raw(item: Any) -> TicketMedia | None:
    if isinstance(item, str):
        stripped = item.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            media_id = int(stripped)
            return TicketMedia(photo_id=media_id, media_id=media_id)
        return TicketMedia(token=stripped)

    if not isinstance(item, dict):
        return None

    token = item.get("token")
    media = TicketMedia(
        photo_id=_int_from_value(item.get("photo_id")),
        media_id=_int_from_value(item.get("media_id")),
        token=token.strip() if isinstance(token, str) and token.strip() else None,
    )
    return media if media.is_valid() else None


def _media_from_draft_json(draft_json: str) -> list[TicketMedia]:
    try:
        data = json.loads(draft_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []

    media = data.get("media")
    if not isinstance(media, list):
        return []

    result: list[TicketMedia] = []
    for item in media:
        parsed = _ticket_media_from_raw(item)
        if parsed is None:
            continue
        if any(existing.matches(parsed) for existing in result):
            continue
        result.append(parsed)
    return result


def _draft_json_from_media(media: list[TicketMedia]) -> str:
    payload = [
        item.model_dump(exclude_none=True)
        for item in media
        if item.is_valid()
    ]
    return json.dumps({"media": payload}, ensure_ascii=False)


class TicketStorage:
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._db = connection

    async def get_draft(self, chat_id: int) -> TicketDraft | None:
        session = await self.get_session(chat_id)
        if session is None:
            return None
        return session.draft

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
            draft=TicketDraft(
                topic=row[2],
                description=row[3],
                contact=row[4],
                urgency=row[5],
                media=_media_from_draft_json(draft_json),
            ),
        )

    async def save_session(self, session: TicketSession) -> None:
        await self._db.execute(
            """
            INSERT INTO ticket_sessions (
                chat_id, state, topic, description, contact, urgency, draft_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                state = excluded.state,
                topic = excluded.topic,
                description = excluded.description,
                contact = excluded.contact,
                urgency = excluded.urgency,
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
                _draft_json_from_media(session.draft.media),
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