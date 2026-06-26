from __future__ import annotations

import logging
from typing import Any

from app.tickets.models import TicketDraft, TicketMedia

logger = logging.getLogger(__name__)

_IMAGE_ATTACHMENT_TYPES = {"image", "photo"}
_KEYBOARD_ATTACHMENT_TYPES = {"inline_keyboard"}


def int_from_value(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def token_from_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def extract_token_from_payload(payload: dict[str, Any]) -> str | None:
    token = token_from_value(payload.get("token"))
    if token:
        return token

    photos = payload.get("photos")
    if isinstance(photos, dict):
        for photo_data in photos.values():
            if not isinstance(photo_data, dict):
                continue
            token = token_from_value(photo_data.get("token"))
            if token:
                return token

    return None


def ticket_media_from_payload(payload: dict[str, Any]) -> TicketMedia | None:
    token = extract_token_from_payload(payload)
    photo_id = int_from_value(payload.get("photo_id"))
    media_id = int_from_value(payload.get("media_id"))

    if token is None and photo_id is None and media_id is None:
        return None

    logger.debug(
        "media parsed: photo_id=%s media_id=%s token_present=%s payload_keys=%s",
        photo_id,
        media_id,
        bool(token),
        sorted(payload.keys()),
    )

    return TicketMedia(photo_id=photo_id, media_id=media_id, token=token)


def ticket_media_from_raw(item: Any) -> TicketMedia | None:
    if isinstance(item, str):
        stripped = item.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            media_id = int(stripped)
            return TicketMedia(photo_id=media_id, media_id=media_id)
        return TicketMedia(token=stripped)

    if isinstance(item, dict):
        return ticket_media_from_payload(item)

    media_id = int_from_value(item)
    if media_id is not None:
        return TicketMedia(photo_id=media_id, media_id=media_id)

    return None


def ticket_media_from_attachment(item: dict[str, Any]) -> TicketMedia | None:
    att_type = str(item.get("type", ""))
    if att_type in _KEYBOARD_ATTACHMENT_TYPES:
        return None
    if att_type not in _IMAGE_ATTACHMENT_TYPES:
        return None

    payload = item.get("payload")
    if isinstance(payload, dict):
        parsed = ticket_media_from_payload(payload)
        if parsed is not None:
            return parsed

    token = token_from_value(item.get("token"))
    photo_id = int_from_value(item.get("photo_id"))
    media_id = int_from_value(item.get("media_id"))
    if token is None and photo_id is None and media_id is None:
        return None

    return TicketMedia(photo_id=photo_id, media_id=media_id, token=token)


def dedupe_media(items: list[TicketMedia]) -> list[TicketMedia]:
    result: list[TicketMedia] = []
    for item in items:
        if any(existing.matches(item) for existing in result):
            continue
        result.append(item)
    return result


def append_ticket_media(draft: TicketDraft, item: TicketMedia) -> bool:
    if not item.is_forwardable():
        return False

    for index, existing in enumerate(draft.media):
        if not existing.matches(item):
            continue

        merged = existing.merge(item)
        if merged == existing:
            return False

        draft.media[index] = merged
        return True

    draft.media.append(item)
    return True


def extract_ticket_media(update: dict[str, Any]) -> list[TicketMedia]:
    media_items: list[TicketMedia] = []

    media = update.get("media")
    if isinstance(media, list):
        for item in media:
            parsed = ticket_media_from_raw(item)
            if parsed is not None:
                media_items.append(parsed)

    message = update.get("message")
    if isinstance(message, dict):
        body = message.get("body")
        if isinstance(body, dict):
            attachments = body.get("attachments")
            if isinstance(attachments, list):
                for attachment in attachments:
                    if not isinstance(attachment, dict):
                        continue
                    parsed = ticket_media_from_attachment(attachment)
                    if parsed is not None:
                        media_items.append(parsed)

    return dedupe_media(media_items)