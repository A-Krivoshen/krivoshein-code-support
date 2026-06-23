from __future__ import annotations

from app.bot.states import TicketState
from app.tickets.models import TicketDraft, TicketSession


class InMemoryTicketStorage:
    def __init__(self) -> None:
        self._sessions: dict[int, TicketSession] = {}

    def get_session(self, chat_id: int) -> TicketSession | None:
        return self._sessions.get(chat_id)

    def get_or_create_session(self, chat_id: int) -> TicketSession:
        session = self._sessions.get(chat_id)
        if session is None:
            session = TicketSession(chat_id=chat_id)
            self._sessions[chat_id] = session
        return session

    def set_session(self, session: TicketSession) -> None:
        self._sessions[session.chat_id] = session

    def clear_session(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)

    def has_active_ticket_flow(self, chat_id: int) -> bool:
        session = self._sessions.get(chat_id)
        return session is not None and session.state != TicketState.IDLE