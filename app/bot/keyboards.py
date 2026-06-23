from __future__ import annotations

from typing import Any

from app.bot.faq import FAQ_PRICE, FAQ_REQUEST, FAQ_SUPPORT, FAQ_TIMELINE

MENU_TICKET = "menu:ticket"
MENU_FAQ = "menu:faq"
MENU_DOCS = "menu:docs"
MENU_OTHER = "menu:other"
MENU_MAIN = "menu:main"

TICKET_TOPIC_SUPPORT = "ticket:topic:support"
TICKET_TOPIC_CONSULT = "ticket:topic:consult"
TICKET_TOPIC_OTHER = "ticket:topic:other"
TICKET_CONFIRM_SEND = "ticket:confirm:send"
TICKET_CONFIRM_CANCEL = "ticket:confirm:cancel"

MENU_LABELS = {
    MENU_TICKET: "Подать заявку",
    MENU_FAQ: "Частые вопросы",
    MENU_DOCS: "Документация",
    MENU_OTHER: "Другое",
}

TICKET_TOPIC_LABELS = {
    TICKET_TOPIC_SUPPORT: "Техподдержка",
    TICKET_TOPIC_CONSULT: "Консультация",
    TICKET_TOPIC_OTHER: "Другое",
}


def callback_button(text: str, payload: str) -> dict[str, str]:
    return {"type": "callback", "text": text, "payload": payload}


def get_main_menu() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [callback_button("Подать заявку", MENU_TICKET)],
                [callback_button("Частые вопросы", MENU_FAQ)],
                [callback_button("Документация", MENU_DOCS)],
                [callback_button("Другое", MENU_OTHER)],
            ],
        },
    }


def get_ticket_topic_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [callback_button("Техподдержка", TICKET_TOPIC_SUPPORT)],
                [callback_button("Консультация", TICKET_TOPIC_CONSULT)],
                [callback_button("Другое", TICKET_TOPIC_OTHER)],
            ],
        },
    }


def get_faq_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [callback_button("Сколько стоит сайт?", FAQ_PRICE)],
                [callback_button("Сроки разработки", FAQ_TIMELINE)],
                [callback_button("Техподдержка", FAQ_SUPPORT)],
                [callback_button("Как подать заявку?", FAQ_REQUEST)],
                [callback_button("Назад в меню", MENU_MAIN)],
            ],
        },
    }


def get_faq_back_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [callback_button("Назад в главное меню", MENU_MAIN)],
            ],
        },
    }


def get_ticket_confirm_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    callback_button("Отправить", TICKET_CONFIRM_SEND),
                    callback_button("Отменить", TICKET_CONFIRM_CANCEL),
                ],
            ],
        },
    }