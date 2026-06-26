from __future__ import annotations

import json
import logging
from typing import Any

from app.tickets.media import ticket_media_from_raw
from app.tickets.models import TicketDraft, TicketMedia

logger = logging.getLogger(__name__)

_DRAFT_FIELDS = ("topic", "description", "contact", "urgency")


def serialize_draft(draft: TicketDraft) -> str:
    payload = draft.model_dump(mode="json")
    payload["media"] = [
        item.model_dump(exclude_none=True)
        for item in draft.media
        if item.is_valid()
    ]
    return json.dumps(payload, ensure_ascii=False)


def _media_from_json_data(data: dict[str, Any]) -> list[TicketMedia]:
    media = data.get("media")
    if not isinstance(media, list):
        return []

    result: list[TicketMedia] = []
    for item in media:
        parsed = ticket_media_from_raw(item)
        if parsed is None:
            continue
        if any(existing.matches(parsed) for existing in result):
            continue
        result.append(parsed)
    return result


def _draft_has_fields(data: dict[str, Any]) -> bool:
    return any(field in data for field in _DRAFT_FIELDS)


def deserialize_draft(
    draft_json: str,
    *,
    topic: str = "",
    description: str = "",
    contact: str = "",
    urgency: str = "",
) -> TicketDraft:
    data: dict[str, Any] = {}
    if draft_json:
        try:
            parsed = json.loads(draft_json)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            logger.warning("Некорректный draft_json, используем legacy-поля")

    if _draft_has_fields(data):
        media = _media_from_json_data(data)
        return TicketDraft(
            topic=str(data.get("topic") or ""),
            description=str(data.get("description") or ""),
            contact=str(data.get("contact") or ""),
            urgency=str(data.get("urgency") or ""),
            media=media,
        )

    return TicketDraft(
        topic=topic,
        description=description,
        contact=contact,
        urgency=urgency,
        media=_media_from_json_data(data),
    )