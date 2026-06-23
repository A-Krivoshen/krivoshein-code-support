from __future__ import annotations

from dataclasses import dataclass, field

from app.bot.states import TicketState


@dataclass(slots=True)
class TicketDraft:
    topic: str = ""
    description: str = ""
    contact: str = ""


@dataclass(slots=True)
class TicketSession:
    chat_id: int
    state: TicketState = TicketState.IDLE
    draft: TicketDraft = field(default_factory=TicketDraft)