from __future__ import annotations

from app.tickets.models import TicketDraft


def format_summary(draft: TicketDraft) -> str:
    return (
        "Проверьте заявку перед отправкой:\n\n"
        f"Тема: {draft.topic}\n"
        f"Описание: {draft.description}\n"
        f"Контакт: {draft.contact}\n\n"
        "Отправить заявку?"
    )


def format_admin_message(draft: TicketDraft, chat_id: int) -> str:
    return (
        "Новая заявка\n"
        "────────────\n"
        f"Chat ID: {chat_id}\n"
        f"Тема: {draft.topic}\n"
        f"Описание:\n{draft.description}\n\n"
        f"Контакт: {draft.contact}"
    )