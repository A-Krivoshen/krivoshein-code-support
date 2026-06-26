from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.max_api.client import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.tickets.models import TicketDraft, TicketMedia

logger = logging.getLogger(__name__)

URGENCY_EMOJI = {
    "Обычная": "🟢",
    "Срочно": "🟡",
    "Очень срочно": "🔴",
}


def _format_urgency(urgency: str) -> tuple[str, str]:
    label = urgency or "—"
    return label, URGENCY_EMOJI.get(label, "⚪")


@dataclass(slots=True)
class TicketSendResult:
    text_sent: bool
    media_sent: int
    media_failed: int
    media_total: int


def _screenshot_label(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "скриншот"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "скриншота"
    return "скриншотов"


def format_summary(draft: TicketDraft) -> str:
    urgency, urgency_emoji = _format_urgency(draft.urgency)
    lines = [
        "📋 Ваша заявка",
        "",
        f"📌 {draft.topic}  ·  {urgency_emoji} {urgency}",
        f"📝 {draft.description}",
    ]
    forwardable_media = draft.forwardable_media()
    if forwardable_media:
        count = len(forwardable_media)
        lines.append(f"🖼 {count} {_screenshot_label(count)}")
    lines.extend(
        [
            f"📞 {draft.contact}",
            "",
            "Всё верно? Нажмите «Отправить» 👇",
        ]
    )
    return "\n".join(lines)


def format_admin_message(draft: TicketDraft, chat_id: int) -> str:
    urgency, urgency_emoji = _format_urgency(draft.urgency)
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
    forwardable_media = draft.forwardable_media()
    if forwardable_media:
        lines.append(f"🖼 Прикреплено изображений: {len(forwardable_media)}")
    return "\n".join(lines)


async def _forward_ticket_media_item(
    client: MaxApiClient,
    admin_channel_id: int,
    item: TicketMedia,
    *,
    index: int,
    total: int,
) -> bool:
    if not item.has_token():
        logger.warning(
            "Пропущено медиа без token %s/%s для admin_channel_id=%s (photo_id=%s, media_id=%s)",
            index,
            total,
            admin_channel_id,
            item.photo_id,
            item.media_id,
        )
        return False

    try:
        await client.forward_ticket_image(admin_channel_id, token=item.token)
        return True
    except MaxApiError:
        logger.exception(
            "Не удалось переслать изображение %s/%s в admin_channel_id=%s "
            "(photo_id=%s, media_id=%s)",
            index,
            total,
            admin_channel_id,
            item.photo_id,
            item.media_id,
        )
        return False


async def send_ticket_to_admin(
    client: MaxApiClient,
    admin_channel_id: int,
    draft: TicketDraft,
    chat_id: int,
) -> TicketSendResult:
    media_total = len(draft.forwardable_media())
    admin_text = format_admin_message(draft, chat_id)

    try:
        await client.send_channel_message(admin_channel_id, admin_text)
    except MaxApiError:
        logger.exception(
            "Не удалось отправить текст заявки в admin_channel_id=%s",
            admin_channel_id,
        )
        return TicketSendResult(
            text_sent=False,
            media_sent=0,
            media_failed=media_total,
            media_total=media_total,
        )

    media_sent = 0
    media_failed = 0
    for index, item in enumerate(draft.forwardable_media(), start=1):
        if await _forward_ticket_media_item(
            client,
            admin_channel_id,
            item,
            index=index,
            total=media_total,
        ):
            media_sent += 1
        else:
            media_failed += 1

    return TicketSendResult(
        text_sent=True,
        media_sent=media_sent,
        media_failed=media_failed,
        media_total=media_total,
    )