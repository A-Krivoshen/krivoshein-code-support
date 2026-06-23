from __future__ import annotations

from pydantic import BaseModel, Field

from app.bot.states import TicketState


class TicketDraft(BaseModel):
    topic: str = ""
    description: str = ""
    contact: str = ""
    urgency: str = ""


class TicketSession(BaseModel):
    chat_id: int
    state: TicketState = TicketState.IDLE
    draft: TicketDraft = Field(default_factory=TicketDraft)