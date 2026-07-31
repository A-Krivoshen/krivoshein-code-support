from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.config import Settings, settings

if TYPE_CHECKING:
    from app.llm.gigachat import GigaChatClient

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
    """OpenAI-compatible Chat Completions (Groq) with optional GigaChat fallback."""

    def __init__(
        self,
        config: Settings | None = None,
        *,
        gigachat: GigaChatClient | None = None,
    ) -> None:
        self._settings = config or settings
        base = self._settings.llm_base_url.rstrip("/")
        self._url = f"{base}/chat/completions"
        self._http = httpx.AsyncClient(timeout=self._settings.llm_timeout)
        self._gigachat = gigachat
        self._owns_gigachat = False
        self.last_provider: str | None = None

        if self._gigachat is None and self._settings.gigachat_enabled:
            # Lazy import avoids circular dependency at module load.
            from app.llm.gigachat import GigaChatClient as _GigaChatClient

            self._gigachat = _GigaChatClient(self._settings)
            self._owns_gigachat = True

    async def aclose(self) -> None:
        await self._http.aclose()
        if self._owns_gigachat and self._gigachat is not None:
            await self._gigachat.aclose()

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Try Groq first; on failure fall back to GigaChat when enabled."""
        primary_error: LlmError | None = None
        try:
            text = await self._chat_groq(messages, **kwargs)
            self.last_provider = "groq"
            logger.info(
                "LLM answered provider=groq model=%s",
                kwargs.get("model", self._settings.llm_model),
            )
            return text
        except LlmError as exc:
            primary_error = exc
            logger.warning(
                "LLM primary failed provider=groq status=%s error=%s",
                getattr(exc, "status_code", None),
                exc,
            )

        if self._can_use_gigachat():
            try:
                assert self._gigachat is not None
                giga_kwargs = dict(kwargs)
                # Never send Groq model id to GigaChat.
                giga_kwargs["model"] = self._settings.gigachat_model
                text = await self._gigachat.chat(messages, **giga_kwargs)
                self.last_provider = "gigachat"
                logger.info(
                    "LLM answered provider=gigachat model=%s",
                    self._settings.gigachat_model,
                )
                return text
            except LlmError as exc:
                logger.warning(
                    "LLM fallback failed provider=gigachat status=%s error=%s",
                    getattr(exc, "status_code", None),
                    exc,
                )
                raise
            except Exception:
                logger.exception("LLM fallback unexpected error provider=gigachat")
                raise

        assert primary_error is not None
        raise primary_error

    def _can_use_gigachat(self) -> bool:
        return (
            self._gigachat is not None
            and self._settings.gigachat_enabled
            and self._gigachat.is_configured
        )

    async def _chat_groq(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
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
            logger.warning(
                "LLM request timed out (timeout=%s)", self._settings.llm_timeout
            )
            raise LlmRequestError("LLM request timed out") from exc
        except httpx.RequestError as exc:
            # Не логируем headers/body — там может быть Authorization.
            logger.warning("LLM transport error: %s", type(exc).__name__)
            raise LlmRequestError(
                f"LLM transport error: {type(exc).__name__}"
            ) from exc

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
