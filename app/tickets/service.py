from __future__ import annotations

from datetime import UTC, datetime

from app.tickets.models import TicketDraft

URGENCY_EMOJI = {
    "Обычная": "🟢",
    "Срочно": "🟡",
    "Очень срочно": "🔴",
}


def format_summary(draft: TicketDraft) -> str:
    return (
        "Проверьте данные заявки перед отправкой:\n\n"
        f"📌 Тема: {draft.topic}\n"
        f"📝 Описание:\n{draft.description}\n"
        f"📞 Контакт: {draft.contact}\n"
        f"⚡ Срочность: {draft.urgency}"
    )


def format_admin_message(draft: TicketDraft, chat_id: int) -> str:
    urgency = draft.urgency or "—"
    urgency_emoji = URGENCY_EMOJI.get(urgency, "⚪")
    created_label = datetime.now(UTC).strftime("%d.%m.%Y %H:%M")

    return (
        "📋 Новая заявка\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📌 Тема: {draft.topic}\n"
        f"{urgency_emoji} Срочность: {urgency}\n"
        f"🆔 Chat ID: {chat_id}\n"
        f"📞 Контакт: {draft.contact}\n"
        "📝 Описание:\n"
        f"{draft.description}\n"
        f"🕐 {created_label}"
    )