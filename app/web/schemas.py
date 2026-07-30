"""Pydantic models for web assistant API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class BootstrapRequest(BaseModel):
    host: str = Field(..., min_length=1, max_length=253)
    path: str = Field(default='/', max_length=500)
    session_id: str | None = Field(default=None, max_length=64)


class HandoffLinks(BaseModel):
    telegram_url: str
    telegram_label: str
    max_url: str
    max_label: str
    contacts_url: str
    contacts_label: str
    price_url: str


class BootstrapResponse(BaseModel):
    session_id: str
    host: str
    site_key: str
    site_label: str
    greeting: str
    quick_replies: list[str]
    handoff: HandoffLinks
    title: str = "\u041f\u043e\u043c\u043e\u0449\u043d\u0438\u043a Dr.Slon"
    subtitle: str = "\u0423\u0441\u043b\u0443\u0433\u0438 \u0438 \u0437\u0430\u044f\u0432\u043a\u0438"


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    host: str = Field(..., min_length=1, max_length=253)
    path: str = Field(default='/', max_length=500)
    message: str = Field(..., min_length=1, max_length=2000)
    website: str = Field(default="", max_length=200)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("empty message")
        return text


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    suggest_lead: bool = False
    quick_replies: list[str] = Field(default_factory=list)


class LeadRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    host: str = Field(..., min_length=1, max_length=253)
    path: str = Field(default='/', max_length=500)
    topic: str = Field(default="", max_length=200)
    need: str = Field(..., min_length=3, max_length=4000)
    budget: str = Field(default="", max_length=200)
    urgency: str = Field(default="\u041e\u0431\u044b\u0447\u043d\u0430\u044f", max_length=50)
    contact: str = Field(..., min_length=3, max_length=300)
    website: str = Field(default="", max_length=200)

    @field_validator("need", "contact")
    @classmethod
    def strip_required(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("required")
        return text


class LeadResponse(BaseModel):
    ok: bool
    lead_id: int | None = None
    message: str
    handoff: HandoffLinks | None = None
