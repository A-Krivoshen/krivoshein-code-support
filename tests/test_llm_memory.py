from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.llm.memory import ChatMemory
from app.llm.service import LlmReplyResult, LlmService
from app.llm.topic_infer import (
    build_description_from_user_texts,
    infer_topic_label,
    infer_topic_payload,
)
from app.bot.keyboards import TICKET_TOPIC_VPS, TICKET_TOPIC_WORDPRESS


@pytest.fixture
async def memory(db_connection):
    return ChatMemory(db_connection)


async def test_rate_limit_blocks_after_limit(memory):
    chat_id = 100
    for _ in range(8):
        assert not await memory.is_rate_limited(chat_id, limit_per_hour=8)
        await memory.record_request(chat_id)

    assert await memory.is_rate_limited(chat_id, limit_per_hour=8)


async def test_history_trim_keeps_last_n(memory):
    chat_id = 101
    for i in range(12):
        role = "user" if i % 2 == 0 else "assistant"
        await memory.append_message(chat_id, role, f"msg-{i}")

    await memory.trim_history(chat_id, max_messages=6, ttl_hours=24)
    messages = await memory.get_recent_messages(chat_id, max_messages=20, ttl_hours=24)
    assert len(messages) == 6
    assert messages[-1]["content"] == "msg-11"


async def test_history_ttl_excludes_old(memory, db_connection):
    chat_id = 102
    old = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    await db_connection.execute(
        "INSERT INTO chat_history (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, "user", "old", old),
    )
    await db_connection.commit()
    await memory.append_message(chat_id, "user", "new")

    messages = await memory.get_recent_messages(chat_id, max_messages=10, ttl_hours=24)
    assert len(messages) == 1
    assert messages[0]["content"] == "new"


async def test_llm_service_rate_limit_no_client_call(memory, monkeypatch):
    client = AsyncMock()
    client.chat = AsyncMock(return_value="ok")

    class Cfg:
        llm_enabled = True
        llm_api_key = "test-key"
        llm_rate_limit_per_hour = 2
        llm_history_pairs = 5
        llm_history_ttl_hours = 24

    service = LlmService(client=client, config=Cfg(), memory=memory)  # type: ignore[arg-type]
    await memory.record_request(50)
    await memory.record_request(50)

    result = await service.reply("вопрос", chat_id=50)
    assert result.rate_limited is True
    client.chat.assert_not_awaited()


async def test_llm_service_uses_history(memory, monkeypatch):
    client = AsyncMock()
    client.chat = AsyncMock(return_value="ответ 2")

    class Cfg:
        llm_enabled = True
        llm_api_key = "test-key"
        llm_rate_limit_per_hour = 8
        llm_history_pairs = 5
        llm_history_ttl_hours = 24

    service = LlmService(client=client, config=Cfg(), memory=memory)  # type: ignore[arg-type]
    await memory.append_message(51, "user", "первый")
    await memory.append_message(51, "assistant", "ответ 1")

    result = await service.reply("второй", chat_id=51)
    assert result.ok
    assert result.text == "ответ 2"
    messages = client.chat.await_args.args[0]
    roles = [m["role"] for m in messages]
    assert roles[0] == "system"
    assert "первый" in [m["content"] for m in messages]
    assert messages[-1] == {"role": "user", "content": "второй"}


def test_infer_topic_wordpress():
    assert infer_topic_payload("сайт на wordpress тормозит, плагин") == TICKET_TOPIC_WORDPRESS
    assert infer_topic_label("wordpress acf") == "WordPress / Поддержка сайта"


def test_infer_topic_vps():
    assert infer_topic_payload("нужен VPS nginx docker") == TICKET_TOPIC_VPS


def test_infer_topic_tie_returns_none():
    # одинаковое число совпадений по двум темам — не угадываем
    assert infer_topic_payload("wordpress vps") is None


def test_build_description_order():
    texts = ["новый вопрос", "старый вопрос"]  # newest first
    desc = build_description_from_user_texts(texts)
    assert desc.index("старый") < desc.index("новый")
