from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.bot.keyboards import MENU_TICKET, TICKET_CONFIRM_SEND, TICKET_TOPIC_SUPPORT
from app.bot.router import BotRouter
from app.bot.states import TicketState
from app.tickets.models import TicketDraft, TicketSession
from app.tickets.storage import TicketStorage


@pytest.fixture
def api_client():
    return AsyncMock()


@pytest.fixture
def router(api_client, storage):
    return BotRouter(api_client, storage)


async def test_handle_bot_started_sends_menu(router, api_client):
    await router.handle_update({"update_type": "bot_started", "chat_id": 10})

    api_client.send_message.assert_awaited()
    args = api_client.send_message.await_args
    assert args.args[0] == 10


async def test_start_ticket_flow_creates_session(router, storage, api_client):
    await router.handle_update(
        {
            "update_type": "message_callback",
            "chat_id": 11,
            "callback": {"payload": MENU_TICKET},
        }
    )

    session = await storage.get_session(11)
    assert session is not None
    assert session.state == TicketState.TICKET_TOPIC
    api_client.send_message.assert_awaited()


async def test_ticket_topic_callback_advances_state(router, storage, api_client):
    await storage.save_session(
        TicketSession(
            chat_id=12,
            state=TicketState.TICKET_TOPIC,
            draft=TicketDraft(),
        )
    )

    await router.handle_update(
        {
            "update_type": "message_callback",
            "chat_id": 12,
            "callback": {"payload": TICKET_TOPIC_SUPPORT},
        }
    )

    session = await storage.get_session(12)
    assert session is not None
    assert session.state == TicketState.TICKET_DESCRIPTION
    assert session.draft.topic == "Техподдержка"


async def test_submit_ticket_without_admin_channel(router, storage, api_client, monkeypatch):
    monkeypatch.setattr("app.bot.router.settings.admin_channel_id", None)

    await storage.save_session(
        TicketSession(
            chat_id=13,
            state=TicketState.TICKET_CONFIRM,
            draft=TicketDraft(
                topic="Техподдержка",
                description="Проблема",
                contact="user@example.com",
                urgency="Обычная",
            ),
        )
    )

    await router.handle_update(
        {
            "update_type": "message_callback",
            "chat_id": 13,
            "callback": {"payload": TICKET_CONFIRM_SEND},
        }
    )

    session = await storage.get_session(13)
    assert session is not None
    assert session.state == TicketState.TICKET_CONFIRM
    assert "админ-канал" in api_client.send_message.await_args.args[1].lower()