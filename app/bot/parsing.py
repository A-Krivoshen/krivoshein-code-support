from __future__ import annotations

import re
from typing import Any

from app.bot.texts import BTN_TO_MENU

START_COMMAND = "/start"
MENU_RESET_COMMANDS = frozenset(
    {START_COMMAND, "start", "старт", "меню", BTN_TO_MENU.lower()}
)

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


def extract_chat_id(update: dict[str, Any]) -> int | None:
    chat_id = update.get("chat_id")
    if isinstance(chat_id, int):
        return chat_id

    message = update.get("message")
    if isinstance(message, dict):
        recipient = message.get("recipient")
        if isinstance(recipient, dict):
            recipient_chat_id = recipient.get("chat_id")
            if isinstance(recipient_chat_id, int):
                return recipient_chat_id

    callback = update.get("callback")
    if isinstance(callback, dict):
        callback_message = callback.get("message")
        if isinstance(callback_message, dict):
            recipient = callback_message.get("recipient")
            if isinstance(recipient, dict):
                recipient_chat_id = recipient.get("chat_id")
                if isinstance(recipient_chat_id, int):
                    return recipient_chat_id

    return None


def extract_message_text(update: dict[str, Any]) -> str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    body = message.get("body")
    if not isinstance(body, dict):
        return None

    text = body.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    return None


def extract_callback_payload(update: dict[str, Any]) -> str | None:
    callback = update.get("callback")
    if not isinstance(callback, dict):
        return None

    payload = callback.get("payload")
    if isinstance(payload, str) and payload.strip():
        return payload.strip()

    return None


def is_reset_command(text: str | None) -> bool:
    if not text:
        return False
    return text.strip().lower() in MENU_RESET_COMMANDS


def is_valid_contact(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    if _EMAIL_RE.match(normalized):
        return True
    digits = re.sub(r"\D", "", normalized)
    return len(digits) >= 10 and _PHONE_RE.match(normalized) is not None