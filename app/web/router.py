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
    BlogRagAskRequest,
    BlogRagAskResponse,
    BlogRagSource,
    BlogRagStatusResponse,
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


def _blog_rag(request: Request):
    svc = getattr(request.app.state, "blog_rag", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Blog RAG unavailable")
    return svc


@router.get("/blog-rag-demo", response_class=FileResponse)
async def blog_rag_demo_page() -> FileResponse:
    """Public demo page: RAG over blog + GigaChat."""
    path = STATIC_DIR / "blog-rag-demo.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Demo page missing")
    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/api/v1/blog-rag/status", response_model=BlogRagStatusResponse)
async def blog_rag_status(request: Request) -> BlogRagStatusResponse:
    _check_origin(request)
    rag = _blog_rag(request)
    await rag.ensure_index()
    st = rag.stats
    return BlogRagStatusResponse(**st)


@router.post("/api/v1/blog-rag/ask", response_model=BlogRagAskResponse)
async def blog_rag_ask(body: BlogRagAskRequest, request: Request) -> BlogRagAskResponse:
    """Demo RAG: retrieve blog chunks → answer (GigaChat preferred). Rate-limited."""
    _check_origin(request)
    rag = _blog_rag(request)
    store = getattr(request.app.state, "web_store", None)
    ip = _client_ip(request)
    rate_key = f"ip:{ip}"

    if store is not None:
        hour_cap = max(1, int(settings.blog_rag_rate_limit_per_hour))
        day_cap = max(hour_cap, int(settings.blog_rag_rate_limit_per_day))
        if await store.is_rate_limited(
            rate_key, kind="blog_rag", limit=hour_cap, window_hours=1.0
        ):
            logger.warning("Blog RAG rate hour ip=%s limit=%s", ip, hour_cap)
            raise HTTPException(
                status_code=429,
                detail=(
                    "Лимит демо: слишком много вопросов за час. "
                    "Напишите в контакты — сделаем такую базу на вашем сайте."
                ),
            )
        if await store.is_rate_limited(
            rate_key, kind="blog_rag", limit=day_cap, window_hours=24.0
        ):
            logger.warning("Blog RAG rate day ip=%s limit=%s", ip, day_cap)
            raise HTTPException(
                status_code=429,
                detail=(
                    "Дневной лимит демо исчерпан. "
                    "Закажите AI-ready / базу знаний: https://ai-ready.krivoshein.site/"
                ),
            )
        await store.record_rate(rate_key, kind="blog_rag")

    result = await rag.ask(body.message)
    sources = [BlogRagSource(**s) for s in (result.get("sources") or [])]
    return BlogRagAskResponse(
        answer=str(result.get("answer") or ""),
        sources=sources,
        provider=str(result.get("provider") or "none"),
        demo_note=str(result.get("demo_note") or ""),
        stats=dict(result.get("stats") or {}),
    )


@router.post("/api/v1/blog-rag/reindex", response_model=BlogRagStatusResponse)
async def blog_rag_reindex(request: Request) -> BlogRagStatusResponse:
    """Rebuild index from WordPress REST (for demos / after many new posts)."""
    _check_origin(request)
    # Simple shared-secret optional: allow from trusted origins only (already _check_origin)
    rag = _blog_rag(request)
    st = await rag.reindex()
    return BlogRagStatusResponse(**st)
