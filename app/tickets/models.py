from __future__ import annotations

from pydantic import BaseModel, Field

from app.bot.states import TicketState


class TicketMedia(BaseModel):
    photo_id: int | None = None
    media_id: int | None = None
    token: str | None = None

    def is_valid(self) -> bool:
        return self.token is not None or self.photo_id is not None or self.media_id is not None

    def has_token(self) -> bool:
        return bool(self.token)

    def is_forwardable(self) -> bool:
        return self.has_token()

    def merge(self, other: TicketMedia) -> TicketMedia:
        return TicketMedia(
            photo_id=self.photo_id if self.photo_id is not None else other.photo_id,
            media_id=self.media_id if self.media_id is not None else other.media_id,
            token=self.token if self.token is not None else other.token,
        )

    def matches(self, other: TicketMedia) -> bool:
        if self.token and other.token and self.token == other.token:
            return True
        if self.photo_id is not None and other.photo_id is not None and self.photo_id == other.photo_id:
            return True
        if self.media_id is not None and other.media_id is not None and self.media_id == other.media_id:
            return True
        return False


class TicketDraft(BaseModel):
    topic: str = ""
    description: str = ""
    contact: str = ""
    urgency: str = ""
    media: list[TicketMedia] = Field(default_factory=list)

    def forwardable_media(self) -> list[TicketMedia]:
        return [item for item in self.media if item.is_forwardable()]


class TicketSession(BaseModel):
    chat_id: int
    state: TicketState = TicketState.IDLE
    draft: TicketDraft = Field(default_factory=TicketDraft)