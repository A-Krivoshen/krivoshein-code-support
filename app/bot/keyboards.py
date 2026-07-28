from __future__ import annotations

from typing import Any

from app.bot.faq import (
    FAQ_BOTS,
    FAQ_CONSULTATION,
    FAQ_DIAGNOSTICS,
    FAQ_DIRECT,
    FAQ_PRICE,
    FAQ_PRIVACY,
    FAQ_REQUEST,
    FAQ_REWORK,
    FAQ_SUPPORT,
    FAQ_TIMELINE,
    FAQ_VPS,
)

MENU_TICKET = "menu:ticket"
MENU_FAQ = "menu:faq"
MENU_FAQ_BACK = "menu:faq_back"
MENU_DOCS = "menu:docs"
MENU_OTHER = "menu:other"
OTHER_TASK = "menu:other_task"
MENU_MAIN = "menu:main"

SITE_URL = "https://krivoshein.site/"
CONTACT_URL = "https://krivoshein.site/contacts/"

# Актуальные payload тем заявки
TICKET_TOPIC_WORDPRESS = "ticket:topic:wordpress"
TICKET_TOPIC_VPS = "ticket:topic:vps"
TICKET_TOPIC_BOTS = "ticket:topic:bots"
TICKET_TOPIC_DIRECT = "ticket:topic:direct"
TICKET_TOPIC_LANDING = "ticket:topic:landing"
TICKET_TOPIC_OTHER = "ticket:topic:other"

# Устаревшие payload (кнопки в старых сообщениях) — обрабатываем для совместимости
TICKET_TOPIC_SUPPORT = "ticket:topic:support"
TICKET_TOPIC_WEBSITE = "ticket:topic:website"
TICKET_TOPIC_ADS = "ticket:topic:ads"

TICKET_URGENCY_NORMAL = "ticket:urgency:normal"
TICKET_URGENCY_URGENT = "ticket:urgency:urgent"
TICKET_URGENCY_VERY_URGENT = "ticket:urgency:very_urgent"

TICKET_CONFIRM_SEND = "ticket:confirm:send"
TICKET_CONFIRM_CANCEL = "ticket:confirm:cancel"
TICKET_DESCRIPTION_NEXT = "ticket:description:next"

MENU_LABELS = {
    MENU_TICKET: "Подать заявку",
    MENU_FAQ: "Частые вопросы",
    MENU_DOCS: "Документация",
    MENU_OTHER: "Другое",
}

# Подписи тем (legacy payload мапятся на актуальные названия)
TICKET_TOPIC_LABELS = {
    TICKET_TOPIC_WORDPRESS: "WordPress / Поддержка сайта",
    TICKET_TOPIC_VPS: "VPS / Серверы",
    TICKET_TOPIC_BOTS: "Боты (MAX / Telegram)",
    TICKET_TOPIC_DIRECT: "Яндекс.Директ",
    TICKET_TOPIC_LANDING: "Лендинги / Сайты под ключ",
    TICKET_TOPIC_OTHER: "Другое",
    # legacy
    TICKET_TOPIC_SUPPORT: "WordPress / Поддержка сайта",
    TICKET_TOPIC_WEBSITE: "Лендинги / Сайты под ключ",
    TICKET_TOPIC_ADS: "Яндекс.Директ",
}

# Только новые кнопки в UI (без legacy payload)
TICKET_TOPIC_BUTTONS: list[tuple[str, str]] = [
    (TICKET_TOPIC_WORDPRESS, TICKET_TOPIC_LABELS[TICKET_TOPIC_WORDPRESS]),
    (TICKET_TOPIC_VPS, TICKET_TOPIC_LABELS[TICKET_TOPIC_VPS]),
    (TICKET_TOPIC_BOTS, TICKET_TOPIC_LABELS[TICKET_TOPIC_BOTS]),
    (TICKET_TOPIC_DIRECT, TICKET_TOPIC_LABELS[TICKET_TOPIC_DIRECT]),
    (TICKET_TOPIC_LANDING, TICKET_TOPIC_LABELS[TICKET_TOPIC_LANDING]),
    (TICKET_TOPIC_OTHER, TICKET_TOPIC_LABELS[TICKET_TOPIC_OTHER]),
]

TICKET_URGENCY_LABELS = {
    TICKET_URGENCY_NORMAL: "Обычная",
    TICKET_URGENCY_URGENT: "Срочно",
    TICKET_URGENCY_VERY_URGENT: "Очень срочно",
}


def callback_button(text: str, payload: str) -> dict[str, str]:
    return {"type": "callback", "text": text, "payload": payload}


def link_button(text: str, url: str) -> dict[str, str]:
    return {"type": "link", "text": text, "url": url}


def _cancel_row() -> list[dict[str, str]]:
    return [callback_button("Отменить", TICKET_CONFIRM_CANCEL)]


def get_other_menu_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [link_button("Быстрый контакт", CONTACT_URL)],
                [link_button("Перейти на сайт", SITE_URL)],
                [callback_button("Другая задача", OTHER_TASK)],
                [callback_button("Назад в меню", MENU_MAIN)],
            ],
        },
    }


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


def get_llm_reply_keyboard() -> dict[str, Any]:
    """Кнопки после ответа LLM: заявка / FAQ / меню (существующие payload)."""
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [callback_button("Подать заявку", MENU_TICKET)],
                [callback_button("Частые вопросы", MENU_FAQ)],
                [callback_button("В меню", MENU_MAIN)],
            ],
        },
    }


def get_ticket_topic_keyboard() -> dict[str, Any]:
    buttons = [
        [callback_button(label, payload)]
        for payload, label in TICKET_TOPIC_BUTTONS
    ]
    buttons.append(_cancel_row())
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": buttons},
    }


def get_ticket_nav_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [_cancel_row()],
        },
    }


def get_ticket_description_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [callback_button("Далее", TICKET_DESCRIPTION_NEXT)],
                _cancel_row(),
            ],
        },
    }


def get_ticket_urgency_keyboard() -> dict[str, Any]:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    callback_button("Обычная", TICKET_URGENCY_NORMAL),
                    callback_button("Срочно", TICKET_URGENCY_URGENT),
                ],
                [callback_button("Очень срочно", TICKET_URGENCY_VERY_URGENT)],
                _cancel_row(),
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
                [callback_button("Диагностика сайта", FAQ_DIAGNOSTICS)],
                [callback_button("Консультация", FAQ_CONSULTATION)],
                [callback_button("Доработки существующего сайта", FAQ_REWORK)],
                [callback_button("Техподдержка", FAQ_SUPPORT)],
                [callback_button("Настройка VPS / сервера", FAQ_VPS)],
                [callback_button("Разработка ботов", FAQ_BOTS)],
                [callback_button("Яндекс Директ", FAQ_DIRECT)],
                [callback_button("Формы, cookies, персональные данные", FAQ_PRIVACY)],
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
                [callback_button("К списку вопросов", MENU_FAQ_BACK)],
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