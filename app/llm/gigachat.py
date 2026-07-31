"""GigaChat API client: OAuth token cache + chat/completions."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

import httpx

from app.config import Settings, settings
from app.llm.client import LlmRequestError, LlmResponseError

logger = logging.getLogger(__name__)

# Refresh a minute early so concurrent requests don't race on a near-expiry token.
_TOKEN_SKEW_SECONDS = 60.0


class GigaChatClient:
    """Async GigaChat client with in-memory access_token cache (~30 min TTL)."""

    def __init__(self, config: Settings | None = None) -> None:
        self._settings = config or settings
        verify = bool(self._settings.gigachat_verify_ssl)
        self._http = httpx.AsyncClient(
            timeout=self._settings.gigachat_timeout,
            verify=verify,
        )
        self._token: str | None = None
        # Unix seconds when the cached token expires (from API expires_at).
        self._token_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.gigachat_enabled
            and (self._settings.gigachat_auth_key or "").strip()
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    def _auth_header_value(self) -> str:
        key = (self._settings.gigachat_auth_key or "").strip()
        if not key:
            raise LlmRequestError("GIGACHAT_AUTH_KEY is not configured")
        # Accept raw Base64 or a value that already includes "Basic ".
        if key.lower().startswith("basic "):
            return key
        return f"Basic {key}"

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid access_token, refreshing via OAuth when needed."""
        async with self._lock:
            now = time.time()
            if (
                not force_refresh
                and self._token
                and now < (self._token_expires_at - _TOKEN_SKEW_SECONDS)
            ):
                return self._token

            url = self._settings.gigachat_oauth_url
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": self._auth_header_value(),
            }
            data = {"scope": self._settings.gigachat_scope}

            try:
                response = await self._http.post(url, headers=headers, data=data)
            except httpx.TimeoutException as exc:
                logger.warning("GigaChat OAuth timed out")
                raise LlmRequestError("GigaChat OAuth timed out") from exc
            except httpx.RequestError as exc:
                logger.warning(
                    "GigaChat OAuth transport error: %s", type(exc).__name__
                )
                raise LlmRequestError(
                    f"GigaChat OAuth transport error: {type(exc).__name__}"
                ) from exc

            if response.status_code >= 400:
                logger.warning(
                    "GigaChat OAuth HTTP error: status=%s", response.status_code
                )
                raise LlmRequestError(
                    f"GigaChat OAuth HTTP error ({response.status_code})",
                    status_code=response.status_code,
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise LlmResponseError("GigaChat OAuth returned non-JSON") from exc

            token = payload.get("access_token") if isinstance(payload, dict) else None
            if not isinstance(token, str) or not token.strip():
                raise LlmResponseError("GigaChat OAuth response missing access_token")

            expires_at = payload.get("expires_at")
            if isinstance(expires_at, (int, float)) and expires_at > 0:
                # API returns Unix time in milliseconds when value is huge.
                exp = float(expires_at)
                if exp > 1e12:
                    exp = exp / 1000.0
                self._token_expires_at = exp
            else:
                # Fallback: documented ~30 minute lifetime.
                self._token_expires_at = now + 30 * 60

            self._token = token.strip()
            logger.info(
                "GigaChat OAuth token refreshed expires_in_sec=%.0f",
                max(0.0, self._token_expires_at - now),
            )
            return self._token

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        if not self.is_configured:
            raise LlmRequestError("GigaChat is not configured")

        model = kwargs.get("model", self._settings.gigachat_model)
        max_tokens = kwargs.get("max_tokens", self._settings.llm_max_tokens)
        temperature = kwargs.get("temperature", self._settings.llm_temperature)

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        base = self._settings.gigachat_base_url.rstrip("/")
        url = f"{base}/chat/completions"

        async def _post(token: str) -> httpx.Response:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            return await self._http.post(url, json=body, headers=headers)

        token = await self.get_access_token()
        try:
            response = await _post(token)
        except httpx.TimeoutException as exc:
            logger.warning(
                "GigaChat request timed out (timeout=%s)",
                self._settings.gigachat_timeout,
            )
            raise LlmRequestError("GigaChat request timed out") from exc
        except httpx.RequestError as exc:
            logger.warning("GigaChat transport error: %s", type(exc).__name__)
            raise LlmRequestError(
                f"GigaChat transport error: {type(exc).__name__}"
            ) from exc

        # One retry on 401 with a forced token refresh.
        if response.status_code == 401:
            logger.warning("GigaChat chat got 401; refreshing token and retrying")
            token = await self.get_access_token(force_refresh=True)
            try:
                response = await _post(token)
            except httpx.TimeoutException as exc:
                raise LlmRequestError("GigaChat request timed out") from exc
            except httpx.RequestError as exc:
                raise LlmRequestError(
                    f"GigaChat transport error: {type(exc).__name__}"
                ) from exc

        if response.status_code >= 400:
            logger.warning(
                "GigaChat HTTP error: status=%s model=%s",
                response.status_code,
                model,
            )
            raise LlmRequestError(
                f"GigaChat HTTP error ({response.status_code})",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise LlmResponseError("GigaChat returned non-JSON response") from exc

        return self._extract_assistant_text(payload)

    @staticmethod
    def _extract_assistant_text(payload: Any) -> str:
        if not isinstance(payload, dict):
            raise LlmResponseError("GigaChat response must be a JSON object")

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmResponseError("GigaChat response has no choices")

        first = choices[0]
        if not isinstance(first, dict):
            raise LlmResponseError("GigaChat choice has unexpected shape")

        message = first.get("message")
        if not isinstance(message, dict):
            raise LlmResponseError("GigaChat choice is missing message")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmResponseError("GigaChat assistant content is empty")

        return content.strip()
