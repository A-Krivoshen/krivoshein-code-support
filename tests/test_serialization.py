from __future__ import annotations

import json

from app.tickets.models import TicketDraft, TicketMedia
from app.tickets.serialization import deserialize_draft, serialize_draft


def test_serialize_deserialize_roundtrip():
    draft = TicketDraft(
        topic="Техподдержка",
        description="Не работает форма",
        contact="user@example.com",
        urgency="Срочно",
        media=[TicketMedia(token="tok-1")],
    )
    restored = deserialize_draft(serialize_draft(draft))
    assert restored.topic == draft.topic
    assert restored.description == draft.description
    assert restored.contact == draft.contact
    assert restored.urgency == draft.urgency
    assert len(restored.media) == 1
    assert restored.media[0].token == "tok-1"


def test_deserialize_legacy_columns_and_media_only_json():
    legacy_json = json.dumps({"media": [{"token": "legacy-token"}]})
    draft = deserialize_draft(
        legacy_json,
        topic="Разработка сайта",
        description="Нужен лендинг",
        contact="+79991234567",
        urgency="Обычная",
    )
    assert draft.topic == "Разработка сайта"
    assert draft.description == "Нужен лендинг"
    assert draft.contact == "+79991234567"
    assert draft.urgency == "Обычная"
    assert draft.media[0].token == "legacy-token"


def test_deserialize_invalid_json_falls_back_to_columns():
    draft = deserialize_draft(
        "{not-json",
        topic="Другое",
        description="Описание",
        contact="a@b.c",
        urgency="Срочно",
    )
    assert draft.topic == "Другое"
    assert draft.description == "Описание"
    assert draft.media == []