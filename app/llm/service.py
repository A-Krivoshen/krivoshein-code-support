from __future__ import annotations

import logging

from app.config import Settings, settings
from app.llm.client import LlmClient, LlmError
from app.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LlmService:
    """Тонкая обёртка: system prompt + клиент. Без истории и rate-limit."""

    def __init__(
        self,
        client: LlmClient | None = None,
        config: Settings | None = None,
    ) -> None:
        self._settings = config or settings
        self._client = client or LlmClient(self._settings)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def reply(self, user_text: str) -> str | None:
        """Ответ ассистента или None, если LLM выключен / недоступен / ошибка."""
        if not self._settings.llm_enabled:
            return None

        if not self._settings.llm_api_key:
            logger.warning("LLM enabled but LLM_API_KEY is empty")
            return None

        text = (user_text or "").strip()
        if not text:
            return None

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]

        try:
            return await self._client.chat(messages)
        except LlmError as exc:
            logger.warning("LLM reply failed: %s", exc)
            return None
        except Exception:
            logger.exception("Unexpected LLM error")
            return None
