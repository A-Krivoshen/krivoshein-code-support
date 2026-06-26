from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.bot.texts import TICKET_CONFIRM_TEXT
from app.max_api.exceptions import MaxApiRequestError
from app.tickets.models import TicketDraft, TicketMedia
from app.tickets.service import format_admin_message, format_summary, send_ticket_to_admin


def test_format_summary_includes_media_count():
    draft = TicketDraft(
        topic="Техподдержка",
        description="Описание",
        contact="user@example.com",
        urgency="Срочно",
        media=[TicketMedia(token="t1"), TicketMedia(token="t2")],
    )
    text = format_summary(draft)
    assert "Техподдержка" in text
    assert "2 скриншота" in text
    assert "user@example.com" in text
    assert TICKET_CONFIRM_TEXT in text


def test_format_admin_message_contains_chat_id():
    draft = TicketDraft(
        topic="Разработка сайта",
        description="Нужен лендинг",
        contact="+79991234567",
        urgency="Обычная",
    )
    text = format_admin_message(draft, chat_id=777)
    assert "Chat ID: 777" in text
    assert "Разработка сайта" in text


async def test_send_ticket_to_admin_success():
    client = AsyncMock()
    draft = TicketDraft(
        topic="Другое",
        description="Задача",
        contact="a@b.c",
        urgency="Срочно",
        media=[TicketMedia(token="img-1")],
    )

    result = await send_ticket_to_admin(client, -100, draft, chat_id=42)

    assert result.text_sent is True
    assert result.media_sent == 1
    assert result.media_failed == 0
    client.send_channel_message.assert_awaited_once()
    client.forward_ticket_image.assert_awaited_once_with(-100, token="img-1")


async def test_send_ticket_to_admin_text_failure():
    client = AsyncMock()
    client.send_channel_message.side_effect = MaxApiRequestError("network")

    draft = TicketDraft(
        topic="Другое",
        description="Задача",
        contact="a@b.c",
        urgency="Срочно",
        media=[TicketMedia(token="img-1")],
    )

    result = await send_ticket_to_admin(client, -100, draft, chat_id=42)

    assert result.text_sent is False
    assert result.media_sent == 0
    assert result.media_failed == 1
    client.forward_ticket_image.assert_not_awaited()


async def test_send_ticket_to_admin_partial_media_failure():
    client = AsyncMock()
    client.forward_ticket_image.side_effect = MaxApiRequestError("media failed")

    draft = TicketDraft(
        topic="Другое",
        description="Задача",
        contact="a@b.c",
        urgency="Срочно",
        media=[TicketMedia(token="img-1"), TicketMedia(token="img-2")],
    )

    result = await send_ticket_to_admin(client, -100, draft, chat_id=42)

    assert result.text_sent is True
    assert result.media_sent == 0
    assert result.media_failed == 2