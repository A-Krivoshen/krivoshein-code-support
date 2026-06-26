from __future__ import annotations

import json

from app.bot.states import TicketState
from app.tickets.models import TicketDraft, TicketMedia, TicketSession
from app.tickets.serialization import serialize_draft


async def test_save_and_load_session(storage):
    session = TicketSession(
        chat_id=101,
        state=TicketState.TICKET_DESCRIPTION,
        draft=TicketDraft(
            topic="Техподдержка",
            description="Проблема с сайтом",
            media=[TicketMedia(token="media-token")],
        ),
    )
    await storage.save_session(session)

    loaded = await storage.get_session(101)
    assert loaded is not None
    assert loaded.state == TicketState.TICKET_DESCRIPTION
    assert loaded.draft.topic == "Техподдержка"
    assert loaded.draft.description == "Проблема с сайтом"
    assert loaded.draft.media[0].token == "media-token"


async def test_delete_session(storage):
    session = TicketSession(chat_id=202, state=TicketState.TICKET_TOPIC)
    await storage.save_session(session)
    await storage.delete_session(202)
    assert await storage.get_session(202) is None


async def test_has_active_ticket_flow(storage):
    idle = TicketSession(chat_id=303, state=TicketState.IDLE)
    await storage.save_session(idle)
    assert await storage.has_active_ticket_flow(303) is False

    active = TicketSession(chat_id=404, state=TicketState.TICKET_CONTACT)
    await storage.save_session(active)
    assert await storage.has_active_ticket_flow(404) is True


async def test_legacy_row_migration_on_read(storage, db_connection):
    legacy_draft_json = json.dumps({"media": [{"token": "legacy"}]})
    await db_connection.execute(
        """
        INSERT INTO ticket_sessions (
            chat_id, state, topic, description, contact, urgency, draft_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            505,
            TicketState.TICKET_CONFIRM.value,
            "Контекстная реклама",
            "Нужен аудит",
            "user@test.ru",
            "Очень срочно",
            legacy_draft_json,
            "2026-01-01T00:00:00+00:00",
        ),
    )
    await db_connection.commit()

    loaded = await storage.get_session(505)
    assert loaded is not None
    assert loaded.draft.topic == "Контекстная реклама"
    assert loaded.draft.media[0].token == "legacy"

    await storage.save_session(loaded)
    cursor = await db_connection.execute(
        "SELECT draft_json FROM ticket_sessions WHERE chat_id = ?",
        (505,),
    )
    row = await cursor.fetchone()
    await cursor.close()

    stored = json.loads(row[0])
    assert stored["topic"] == "Контекстная реклама"
    assert stored["description"] == "Нужен аудит"
    assert stored["media"][0]["token"] == "legacy"
    assert serialize_draft(loaded.draft) == row[0]