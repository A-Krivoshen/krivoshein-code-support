from __future__ import annotations

from app.bot.keyboards import (
    TICKET_CONFIRM_CANCEL,
    TICKET_CONFIRM_SEND,
    TICKET_TOPIC_BOTS,
    TICKET_TOPIC_DIRECT,
    TICKET_TOPIC_LANDING,
    TICKET_TOPIC_OTHER,
    TICKET_TOPIC_SUPPORT,
    TICKET_TOPIC_VPS,
    TICKET_TOPIC_WORDPRESS,
    TICKET_TOPIC_LABELS,
    get_ticket_confirm_keyboard,
    get_ticket_topic_keyboard,
)


def test_ticket_confirm_keyboard_single_row_send_first():
    keyboard = get_ticket_confirm_keyboard()
    rows = keyboard["payload"]["buttons"]

    assert len(rows) == 1
    assert len(rows[0]) == 2
    assert rows[0][0]["text"] == "Отправить"
    assert rows[0][0]["payload"] == TICKET_CONFIRM_SEND
    assert rows[0][1]["text"] == "Отменить"
    assert rows[0][1]["payload"] == TICKET_CONFIRM_CANCEL


def test_ticket_topic_keyboard_has_new_topics_without_legacy_payloads():
    keyboard = get_ticket_topic_keyboard()
    rows = keyboard["payload"]["buttons"]
    payloads = [row[0]["payload"] for row in rows if row]

    assert TICKET_TOPIC_WORDPRESS in payloads
    assert TICKET_TOPIC_VPS in payloads
    assert TICKET_TOPIC_BOTS in payloads
    assert TICKET_TOPIC_DIRECT in payloads
    assert TICKET_TOPIC_LANDING in payloads
    assert TICKET_TOPIC_OTHER in payloads
    assert TICKET_CONFIRM_CANCEL in payloads
    # legacy payload не показываем в UI
    assert TICKET_TOPIC_SUPPORT not in payloads

    assert TICKET_TOPIC_LABELS[TICKET_TOPIC_WORDPRESS] == "WordPress / Поддержка сайта"
    assert TICKET_TOPIC_LABELS[TICKET_TOPIC_SUPPORT] == "WordPress / Поддержка сайта"