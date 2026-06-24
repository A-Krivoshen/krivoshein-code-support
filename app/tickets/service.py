from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.max_api.client import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.tickets.models import TicketDraft

logger = logging.getLogger(__name__)

URGENCY_EMOJI = {
    "Обычная": "🟢",
    "Срочно": "🟡",
    "Очень срочно": "🔴",
}


@dataclass(slots=True)
class TicketSendResult:
    text_sent: bool
    media_sent: int
    media_failed: int


def format_summary(draft: TicketDraft) -> str:
    lines = [
        "Проверьте данные заявки перед отправкой:\n",
        f"📌 Тема: {draft.topic}",
        f"📝 Описание:\n{draft.description}",
    ]
    if draft.media:
        lines.append(f"🖼 Прикреплено изображений: {len(draft.media)}")
    lines.extend(
        [
            f"📞 Контакт: {draft.contact}",
            f"⚡ Срочность: {draft.urgency}",
        ]
    )
    return "\n".join(lines)


def format_admin_message(draft: TicketDraft, chat_id: int) -> str:
    urgency = draft.urgency or "—"
    urgency_emoji = URGENCY_EMOJI.get(urgency, "⚪")
    created_label = datetime.now(UTC).strftime("%d.%m.%Y %H:%M")

    lines = [
        "📋 Новая заявка",
        "━━━━━━━━━━━━━━━━",
        f"📌 Тема: {draft.topic}",
        f"{urgency_emoji} Срочность: {urgency}",
        f"🆔 Chat ID: {chat_id}",
        f"📞 Контакт: {draft.contact}",
        "📝 Описание:",
        draft.description,
        f"🕐 {created_label}",
    ]
    if draft.media:
        lines.append(f"🖼 Прикреплено изображений: {len(draft.media)}")
    return "\n".join(lines)


async def send_ticket_to_admin(
    client: MaxApiClient,
    admin_channel_id: int,
    draft: TicketDraft,
    chat_id: int,
) -> TicketSendResult:
    admin_text = format_admin_message(draft, chat_id)

    try:
        await client.send_message(admin_channel_id, admin_text)
    except MaxApiError:
        logger.exception(
            "Не удалось отправить текст заявки в admin_channel_id=%s",
            admin_channel_id,
        )
        return TicketSendResult(text_sent=False, media_sent=0, media_failed=len(draft.media))

    media_sent = 0
    media_failed = 0
    for index, media_id in enumerate(draft.media, start=1):
        try:
            await client.send_message_media(admin_channel_id, media_id)
            media_sent += 1
        except MaxApiError:
            media_failed += 1
            logger.exception(
                "Не удалось переслать изображение %s/%s в admin_channel_id=%s, media_id=%s",
                index,
                len(draft.media),
                admin_channel_id,
                media_id,
            )

    return TicketSendResult(
        text_sent=True,
        media_sent=media_sent,
        media_failed=media_failed,
    )