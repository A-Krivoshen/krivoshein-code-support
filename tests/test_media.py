from __future__ import annotations

from app.tickets.media import (
    append_ticket_media,
    extract_ticket_media,
    ticket_media_from_payload,
    ticket_media_from_raw,
)
from app.tickets.models import TicketDraft, TicketMedia


def test_ticket_media_from_payload_with_token():
    media = ticket_media_from_payload({"token": "abc123"})
    assert media is not None
    assert media.token == "abc123"
    assert media.is_forwardable()


def test_ticket_media_from_payload_with_photos_dict():
    media = ticket_media_from_payload({"photos": {"1": {"token": "photo-token"}}})
    assert media is not None
    assert media.token == "photo-token"


def test_ticket_media_from_raw_digit_string():
    media = ticket_media_from_raw("42")
    assert media is not None
    assert media.photo_id == 42
    assert media.media_id == 42
    assert not media.is_forwardable()


def test_extract_ticket_media_from_attachments():
    update = {
        "message": {
            "body": {
                "attachments": [
                    {"type": "inline_keyboard", "payload": {}},
                    {
                        "type": "image",
                        "payload": {"token": "img-token"},
                    },
                ]
            }
        }
    }
    media_items = extract_ticket_media(update)
    assert len(media_items) == 1
    assert media_items[0].token == "img-token"


def test_extract_ticket_media_deduplicates():
    update = {
        "media": [{"token": "same"}],
        "message": {
            "body": {
                "attachments": [
                    {"type": "image", "payload": {"token": "same"}},
                ]
            }
        },
    }
    media_items = extract_ticket_media(update)
    assert len(media_items) == 1


def test_append_ticket_media_merges_existing():
    draft = TicketDraft(media=[TicketMedia(token="tok", photo_id=1)])
    new_item = TicketMedia(token="tok", media_id=2)
    assert append_ticket_media(draft, new_item) is True
    assert len(draft.media) == 1
    assert draft.media[0].photo_id == 1
    assert draft.media[0].media_id == 2


def test_append_ticket_media_rejects_without_token():
    draft = TicketDraft()
    item = TicketMedia(photo_id=1)
    assert append_ticket_media(draft, item) is False
    assert draft.media == []