from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings, settings
from app.llm.client import LlmClient, LlmError
from app.llm.memory import ChatMemory
from app.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LlmReplyResult:
    """Результат idle-ответа LLM."""

    text: str | None = None
    rate_limited: bool = False
    disabled: bool = False
    error: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.rate_limited and not self.disabled and not self.error


class LlmService:
    """System prompt + client + опционально история и rate-limit (SQLite)."""

    def __init__(
        self,
        client: LlmClient | None = None,
        config: Settings | None = None,
        memory: ChatMemory | None = None,
    ) -> None:
        self._settings = config or settings
        self._client = client or LlmClient(self._settings)
        self._owns_client = client is None
        self._memory = memory

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def reply(self, user_text: str, *, chat_id: int | None = None) -> LlmReplyResult:
        """Ответ ассистента. При chat_id + memory — rate-limit и история."""
        if not self._settings.llm_enabled:
            return LlmReplyResult(disabled=True)

        if not self._settings.llm_api_key:
            logger.warning("LLM enabled but LLM_API_KEY is empty")
            return LlmReplyResult(error=True)

        text = (user_text or "").strip()
        if not text:
            return LlmReplyResult(error=True)

        if chat_id is not None and self._memory is not None:
            try:
                if await self._memory.is_rate_limited(
                    chat_id,
                    limit_per_hour=self._settings.llm_rate_limit_per_hour,
                ):
                    logger.info(
                        "LLM rate limit: chat_id=%s limit=%s/h",
                        chat_id,
                        self._settings.llm_rate_limit_per_hour,
                    )
                    return LlmReplyResult(rate_limited=True)
            except Exception:
                logger.exception("Rate limit check failed chat_id=%s", chat_id)
                # не блокируем диалог из-за сбоя счётчика

        history: list[dict[str, str]] = []
        if chat_id is not None and self._memory is not None:
            try:
                max_messages = max(0, self._settings.llm_history_pairs * 2)
                history = await self._memory.get_recent_messages(
                    chat_id,
                    max_messages=max_messages,
                    ttl_hours=self._settings.llm_history_ttl_hours,
                )
            except Exception:
                logger.exception("History load failed chat_id=%s", chat_id)
                history = []

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": text})

        if chat_id is not None and self._memory is not None:
            try:
                await self._memory.record_request(chat_id)
            except Exception:
                logger.exception("Failed to record LLM request chat_id=%s", chat_id)

        try:
            answer = await self._client.chat(messages)
        except LlmError as exc:
            logger.warning("LLM reply failed: %s", exc)
            return LlmReplyResult(error=True)
        except Exception:
            logger.exception("Unexpected LLM error")
            return LlmReplyResult(error=True)

        if chat_id is not None and self._memory is not None and answer:
            try:
                await self._memory.append_message(chat_id, "user", text)
                await self._memory.append_message(chat_id, "assistant", answer)
                await self._memory.trim_history(
                    chat_id,
                    max_messages=max(0, self._settings.llm_history_pairs * 2),
                    ttl_hours=self._settings.llm_history_ttl_hours,
                )
            except Exception:
                logger.exception("History save failed chat_id=%s", chat_id)

        return LlmReplyResult(text=answer)
