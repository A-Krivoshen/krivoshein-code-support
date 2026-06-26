from __future__ import annotations

from app.bot.parsing import (
    extract_callback_payload,
    extract_chat_id,
    extract_message_text,
    is_reset_command,
    is_valid_contact,
)


def test_extract_chat_id_from_root():
    assert extract_chat_id({"chat_id": 42}) == 42


def test_extract_chat_id_from_message_recipient():
    update = {
        "message": {
            "recipient": {"chat_id": 100},
        }
    }
    assert extract_chat_id(update) == 100


def test_extract_chat_id_from_callback_message():
    update = {
        "callback": {
            "message": {
                "recipient": {"chat_id": 200},
            }
        }
    }
    assert extract_chat_id(update) == 200


def test_extract_chat_id_missing():
    assert extract_chat_id({}) is None


def test_extract_message_text():
    update = {
        "message": {
            "body": {"text": "  hello  "},
        }
    }
    assert extract_message_text(update) == "hello"


def test_extract_message_text_empty():
    assert extract_message_text({"message": {"body": {"text": "   "}}}) is None


def test_extract_callback_payload():
    update = {"callback": {"payload": " menu:ticket "}}
    assert extract_callback_payload(update) == "menu:ticket"


def test_is_reset_command_start():
    assert is_reset_command("/start") is True
    assert is_reset_command("  МЕНЮ ") is True
    assert is_reset_command("В меню") is True


def test_is_reset_command_not_reset():
    assert is_reset_command(None) is False
    assert is_reset_command("опишите проблему") is False


def test_is_valid_contact_email():
    assert is_valid_contact("user@example.com") is True


def test_is_valid_contact_phone():
    assert is_valid_contact("+7 (999) 123-45-67") is True


def test_is_valid_contact_invalid():
    assert is_valid_contact("not-a-contact") is False