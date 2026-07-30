"""FastAPI routes for web AI assistant (+ static widget)."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.config import settings
from app.web.knowledge import normalize_host
from app.web.schemas import (
    BootstrapRequest,
    BootstrapResponse,
    ChatRequest,
    ChatResponse,
    HandoffLinks,
    LeadRequest,
    LeadResponse,
)
from app.web.service import WebAssistantService, is_valid_session_id

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

router = APIRouter(tags=["web-assistant"])


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def _service(request: Request) -> WebAssistantService:
    svc = getattr(request.app.state, "web_assistant", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Web assistant unavailable")
    return svc


def _origin_host(header_value: str | None) -> str | None:
    if not header_value:
        return None
    raw = header_value.strip()
    if not raw.startswith("http"):
        return normalize_host(raw)
    parsed = urlparse(raw)
    return normalize_host(parsed.netloc)


def _check_origin(request: Request) -> None:
    if not settings.web_assistant_enabled:
        raise HTTPException(status_code=503, detail="Web assistant disabled")

    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    host = _origin_host(origin) or _origin_host(referer)
    if not host:
        # curl / server-side without Origin
        return

    allowed_hosts = set()
    for item in settings.web_cors_origin_list():
        if item == "*":
            allowed_hosts.add("*")
            continue
        h = _origin_host(item)
        if h:
            allowed_hosts.add(h)

    if "*" in allowed_hosts:
        return
    if host in allowed_hosts:
        return
    if host == "krivoshein.site" or host.endswith(".krivoshein.site"):
        # default trust ecosystem hosts even if list slightly outdated
        return

    logger.warning("Web API rejected host=%s ip=%s", host, _client_ip(request))
    raise HTTPException(status_code=403, detail="Origin not allowed")


@router.post("/api/v1/bootstrap", response_model=BootstrapResponse)
async def bootstrap(body: BootstrapRequest, request: Request) -> BootstrapResponse:
    _check_origin(request)
    svc = _service(request)
    data = await svc.bootstrap(
        host=body.host,
        path=body.path or "/",
        session_id=body.session_id,
    )
    return BootstrapResponse(
        session_id=data["session_id"],
        host=data["host"],
        site_key=data["site_key"],
        site_label=data["site_label"],
        greeting=data["greeting"],
        quick_replies=data["quick_replies"],
        handoff=HandoffLinks(**data["handoff"]),
        title=data["title"],
        subtitle=data["subtitle"],
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    _check_origin(request)
    if not is_valid_session_id(body.session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id")

    svc = _service(request)
    result = await svc.chat(
        session_id=body.session_id.lower(),
        host=body.host,
        path=body.path or "/",
        message=body.message,
        client_ip=_client_ip(request),
        honeypot=body.website,
        origin=request.headers.get("Origin"),
    )
    return ChatResponse(**result)


@router.post("/api/v1/lead", response_model=LeadResponse)
async def lead(body: LeadRequest, request: Request) -> LeadResponse:
    _check_origin(request)
    if not is_valid_session_id(body.session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id")

    svc = _service(request)
    result = await svc.create_lead(
        session_id=body.session_id.lower(),
        host=body.host,
        path=body.path or "/",
        topic=body.topic,
        need=body.need,
        budget=body.budget,
        urgency=body.urgency,
        contact=body.contact,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("User-Agent") or "",
        honeypot=body.website,
        origin=request.headers.get("Origin"),
    )
    handoff = result.get("handoff")
    return LeadResponse(
        ok=bool(result.get("ok")),
        lead_id=result.get("lead_id"),
        message=str(result.get("message") or ""),
        handoff=HandoffLinks(**handoff) if handoff else None,
    )


@router.get("/widget/krv-assistant.js")
async def widget_js() -> FileResponse:
    path = STATIC_DIR / "krv-assistant.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Widget JS missing")
    return FileResponse(
        path,
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/widget/krv-assistant.css")
async def widget_css() -> FileResponse:
    path = STATIC_DIR / "krv-assistant.css"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Widget CSS missing")
    return FileResponse(
        path,
        media_type="text/css; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )
