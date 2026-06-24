from __future__ import annotations

from typing import Any

import httpx

from app.max_api.exceptions import MaxApiRequestError, MaxApiResponseError
from app.max_api.types import BotInfo, ReplyMarkup, SendMessageResponse


class MaxApiClient:
    def __init__(self, token: str, base_url: str = "https://platform-api.max.ru") -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": token} if token else {},
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self.http.request(method, path, params=params, json=json)
        except httpx.RequestError as exc:
            raise MaxApiRequestError(f"MAX API transport error: {exc}") from exc

        if response.status_code != 200:
            code, message = self._parse_error_payload(response)
            detail = message or response.text or "Unknown MAX API error"
            raise MaxApiRequestError(
                f"MAX API error ({response.status_code}): {detail}",
                status_code=response.status_code,
                code=code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise MaxApiResponseError("MAX API returned non-JSON response") from exc

        if not isinstance(payload, dict):
            raise MaxApiResponseError("MAX API response must be a JSON object")

        return payload

    @staticmethod
    def _parse_error_payload(response: httpx.Response) -> tuple[str | None, str | None]:
        try:
            payload = response.json()
        except ValueError:
            return None, None

        if not isinstance(payload, dict):
            return None, None

        code = payload.get("code")
        message = payload.get("message")
        return (
            code if isinstance(code, str) else None,
            message if isinstance(message, str) else None,
        )

    async def get_me(self) -> BotInfo:
        payload = await self._request("GET", "/me")
        return self._parse_bot_info(payload)

    async def register_webhook(self, url: str, update_types: list[str]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/subscriptions",
            json={"url": url, "update_types": update_types},
        )

    async def get_webhook_subscriptions(self) -> dict[str, Any]:
        return await self._request("GET", "/subscriptions")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: ReplyMarkup | None = None,
    ) -> SendMessageResponse:
        body: dict[str, Any] = {"text": text}

        attachments = self._build_attachments(reply_markup)
        if attachments:
            body["attachments"] = attachments

        payload = await self._request(
            "POST",
            "/messages",
            params={"chat_id": chat_id},
            json=body,
        )
        return self._parse_send_message_response(payload)

    @staticmethod
    def _normalize_media_id(media_id: str | int) -> int:
        if isinstance(media_id, int):
            return media_id
        if isinstance(media_id, str) and media_id.isdigit():
            return int(media_id)
        raise MaxApiRequestError(f"Invalid media_id value: {media_id!r}")

    @staticmethod
    def build_image_token_attachment(token: str) -> dict[str, Any]:
        return {
            "type": "image",
            "payload": {"token": token},
        }

    @staticmethod
    def build_message_media_attachment(media_id: str | int) -> dict[str, Any]:
        return {
            "type": "message_media",
            "payload": {"media_id": MaxApiClient._normalize_media_id(media_id)},
        }

    @staticmethod
    def _build_media_message_body(attachment: dict[str, Any]) -> dict[str, Any]:
        return {
            "attachments": [attachment],
            "notify": False,
        }

    async def send_message_attachment(
        self,
        chat_id: int,
        attachment: dict[str, Any],
    ) -> SendMessageResponse:
        payload = await self._request(
            "POST",
            "/messages",
            params={"chat_id": chat_id},
            json=self._build_media_message_body(attachment),
        )
        return self._parse_send_message_response(payload)

    async def send_message_media(self, chat_id: int, media_id: str | int) -> SendMessageResponse:
        return await self.send_message_attachment(
            chat_id,
            self.build_message_media_attachment(media_id),
        )

    async def forward_ticket_image(
        self,
        chat_id: int,
        *,
        token: str | None = None,
        photo_id: int | None = None,
        media_id: int | None = None,
    ) -> SendMessageResponse:
        if token:
            return await self.send_message_attachment(
                chat_id,
                self.build_image_token_attachment(token),
            )

        ref = media_id if media_id is not None else photo_id
        if ref is not None:
            return await self.send_message_media(chat_id, ref)

        raise MaxApiRequestError("No media reference for ticket image forwarding")

    @staticmethod
    def _build_attachments(reply_markup: ReplyMarkup | None) -> list[dict[str, Any]]:
        if reply_markup is None:
            return []

        if isinstance(reply_markup, list):
            return reply_markup

        return [reply_markup]

    @staticmethod
    def _parse_bot_info(payload: dict[str, Any]) -> BotInfo:
        user_id = payload.get("user_id")
        name = payload.get("name")

        if not isinstance(user_id, int) or not isinstance(name, str):
            raise MaxApiResponseError("MAX API /me response is missing user_id or name")

        username = payload.get("username")
        is_bot = payload.get("is_bot", True)
        description = payload.get("description")

        return BotInfo(
            user_id=user_id,
            name=name,
            username=username if isinstance(username, str) else None,
            is_bot=is_bot if isinstance(is_bot, bool) else True,
            description=description if isinstance(description, str) else None,
        )

    @staticmethod
    def _parse_send_message_response(payload: dict[str, Any]) -> SendMessageResponse:
        message = payload.get("message")
        if not isinstance(message, dict):
            raise MaxApiResponseError("MAX API /messages response is missing message object")
        return {"message": message}