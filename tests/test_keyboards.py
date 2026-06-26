from __future__ import annotations

from app.bot.keyboards import (
    TICKET_CONFIRM_CANCEL,
    TICKET_CONFIRM_SEND,
    get_ticket_confirm_keyboard,
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