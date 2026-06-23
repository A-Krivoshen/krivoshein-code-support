from enum import StrEnum


class TicketState(StrEnum):
    IDLE = "idle"
    TICKET_TOPIC = "ticket_topic"
    TICKET_DESCRIPTION = "ticket_description"
    TICKET_CONTACT = "ticket_contact"
    TICKET_URGENCY = "ticket_urgency"
    TICKET_CONFIRM = "ticket_confirm"