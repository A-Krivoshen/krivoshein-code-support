from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

ReplyMarkup = dict[str, Any] | list[dict[str, Any]]


class SendMessageRequest(TypedDict, total=False):
    text: str
    attachments: list[dict[str, Any]]
    link: dict[str, Any]
    notify: bool
    format: str


class MessageBody(TypedDict, total=False):
    mid: str
    text: str
    attachments: list[dict[str, Any]]


class SendMessageResponse(TypedDict):
    message: MessageBody


@dataclass(slots=True)
class BotInfo:
    user_id: int
    name: str
    username: str | None = None
    is_bot: bool = True
    description: str | None = None