from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, settings

logger = logging.getLogger(__name__)


class LlmError(Exception):
    """Базовая ошибка LLM-клиента."""


class LlmRequestError(LlmError):
    """Транспортная ошибка, таймаут или HTTP 4xx/5xx."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class LlmResponseError(LlmError):
    """Неожиданная или пустая структура ответа API."""


class LlmClient:
    """Минимальный async-клиент OpenAI-compatible Chat Completions (Groq)."""

    def __init__(self, config: Settings | None = None) -> None:
        self._settings = config or settings
        base = self._settings.llm_base_url.rstrip("/")
        self._url = f"{base}/chat/completions"
        self._http = httpx.AsyncClient(timeout=self._settings.llm_timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        api_key = self._settings.llm_api_key
        if not api_key:
            raise LlmRequestError("LLM_API_KEY is not configured")

        model = kwargs.get("model", self._settings.llm_model)
        max_tokens = kwargs.get("max_tokens", self._settings.llm_max_tokens)
        temperature = kwargs.get("temperature", self._settings.llm_temperature)

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._http.post(self._url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            logger.warning("LLM request timed out (timeout=%s)", self._settings.llm_timeout)
            raise LlmRequestError("LLM request timed out") from exc
        except httpx.RequestError as exc:
            # Не логируем headers/body — там может быть Authorization.
            logger.warning("LLM transport error: %s", type(exc).__name__)
            raise LlmRequestError(f"LLM transport error: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            logger.warning(
                "LLM HTTP error: status=%s model=%s",
                response.status_code,
                model,
            )
            raise LlmRequestError(
                f"LLM HTTP error ({response.status_code})",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise LlmResponseError("LLM returned non-JSON response") from exc

        return self._extract_assistant_text(payload)

    @staticmethod
    def _extract_assistant_text(payload: Any) -> str:
        if not isinstance(payload, dict):
            raise LlmResponseError("LLM response must be a JSON object")

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmResponseError("LLM response has no choices")

        first = choices[0]
        if not isinstance(first, dict):
            raise LlmResponseError("LLM choice has unexpected shape")

        message = first.get("message")
        if not isinstance(message, dict):
            raise LlmResponseError("LLM choice is missing message")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmResponseError("LLM assistant content is empty")

        return content.strip()
