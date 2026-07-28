from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.bot.keyboards import (
    MENU_FAQ,
    MENU_MAIN,
    MENU_TICKET,
    TICKET_CONFIRM_SEND,
    TICKET_TOPIC_SUPPORT,
    TICKET_TOPIC_VPS,
    TICKET_TOPIC_WORDPRESS,
)
from app.bot.router import LLM_IDLE_FALLBACK_TEXT, BotRouter
from app.bot.states import TicketState
from app.bot.texts import TICKET_HINT_TOPIC_TEXT
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
            "callback": {"payload": TICKET_TOPIC_WORDPRESS},
        }
    )

    session = await storage.get_session(12)
    assert session is not None
    assert session.state == TicketState.TICKET_DESCRIPTION
    assert session.draft.topic == "WordPress / Поддержка сайта"


async def test_legacy_topic_payload_still_works(router, storage, api_client):
    await storage.save_session(
        TicketSession(
            chat_id=14,
            state=TicketState.TICKET_TOPIC,
            draft=TicketDraft(),
        )
    )

    await router.handle_update(
        {
            "update_type": "message_callback",
            "chat_id": 14,
            "callback": {"payload": TICKET_TOPIC_SUPPORT},
        }
    )

    session = await storage.get_session(14)
    assert session is not None
    assert session.state == TicketState.TICKET_DESCRIPTION
    assert session.draft.topic == "WordPress / Поддержка сайта"


async def test_ticket_topic_free_text_sends_soft_hint(router, storage, api_client):
    await storage.save_session(
        TicketSession(
            chat_id=15,
            state=TicketState.TICKET_TOPIC,
            draft=TicketDraft(),
        )
    )

    await router.handle_update(
        {
            "update_type": "message_created",
            "chat_id": 15,
            "message": {"body": {"text": "нужен VPS под WordPress"}},
        }
    )

    session = await storage.get_session(15)
    assert session is not None
    assert session.state == TicketState.TICKET_TOPIC
    args = api_client.send_message.await_args
    assert args.args[1] == TICKET_HINT_TOPIC_TEXT
    markup = args.kwargs.get("reply_markup")
    assert markup is not None
    payloads = {btn["payload"] for row in markup["payload"]["buttons"] for btn in row}
    assert TICKET_TOPIC_VPS in payloads
    assert TICKET_TOPIC_WORDPRESS in payloads


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


async def test_idle_free_text_uses_llm_when_enabled(api_client, storage, monkeypatch):
    monkeypatch.setattr("app.bot.router.settings.llm_enabled", True)
    llm_service = AsyncMock()
    llm_service.reply = AsyncMock(return_value="Ответ про WordPress")
    router = BotRouter(api_client, storage, llm_service=llm_service)

    await router.handle_update(
        {
            "update_type": "message_created",
            "chat_id": 20,
            "message": {"body": {"text": "Сколько стоит поддержка WordPress?"}},
        }
    )

    llm_service.reply.assert_awaited_once_with("Сколько стоит поддержка WordPress?")
    api_client.send_message.assert_awaited()
    args = api_client.send_message.await_args
    assert args.args[0] == 20
    assert args.args[1] == "Ответ про WordPress"
    markup = args.kwargs.get("reply_markup") or (args.args[2] if len(args.args) > 2 else None)
    assert markup is not None
    buttons = markup["payload"]["buttons"]
    payloads = {btn["payload"] for row in buttons for btn in row}
    assert payloads == {MENU_TICKET, MENU_FAQ, MENU_MAIN}


async def test_idle_free_text_llm_none_uses_fallback(api_client, storage, monkeypatch):
    monkeypatch.setattr("app.bot.router.settings.llm_enabled", True)
    llm_service = AsyncMock()
    llm_service.reply = AsyncMock(return_value=None)
    router = BotRouter(api_client, storage, llm_service=llm_service)

    await router.handle_update(
        {
            "update_type": "message_created",
            "chat_id": 21,
            "message": {"body": {"text": "Привет, нужен VPS"}},
        }
    )

    llm_service.reply.assert_awaited_once()
    args = api_client.send_message.await_args
    assert args.args[1] == LLM_IDLE_FALLBACK_TEXT


async def test_idle_free_text_skips_llm_when_disabled(api_client, storage, monkeypatch):
    monkeypatch.setattr("app.bot.router.settings.llm_enabled", False)
    llm_service = AsyncMock()
    llm_service.reply = AsyncMock(return_value="не должен вызваться")
    router = BotRouter(api_client, storage, llm_service=llm_service)

    await router.handle_update(
        {
            "update_type": "message_created",
            "chat_id": 22,
            "message": {"body": {"text": "Свободный вопрос"}},
        }
    )

    llm_service.reply.assert_not_awaited()
    api_client.send_message.assert_awaited()