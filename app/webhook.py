from __future__ import annotations

import json
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.bot.router import BotRouter
from app.config import settings
from app.db import connect_db, init_db
from app.llm.memory import ChatMemory
from app.llm.service import LlmService
from app.logging_config import setup_logging
from app.max_api import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.tickets.storage import TicketStorage
from app.web.knowledge import KnowledgeLoader
from app.web.router import router as web_router
from app.web.service import WebAssistantService
from app.web.store import WebStore

logger = logging.getLogger(__name__)

WEBHOOK_SECRET_HEADER = "X-Max-Bot-Api-Secret"


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


def _verify_webhook_secret(request: Request) -> None:
    """Отклоняет запросы без валидного секрета MAX (заголовок X-Max-Bot-Api-Secret).

    Без этой проверки POST на /webhook обрабатывает любой отправитель как легитимный
    источник апдейтов — возможны фейковые сообщения и заявки в админ-канал.
    """
    provided = request.headers.get(WEBHOOK_SECRET_HEADER)
    expected = settings.webhook_secret

    if not provided:
        logger.warning(
            "Webhook: отклонён, client_ip=%s, reason=missing_secret",
            _client_ip(request),
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    if not secrets.compare_digest(provided, expected):
        logger.warning(
            "Webhook: отклонён, client_ip=%s, reason=invalid_secret",
            _client_ip(request),
        )
        raise HTTPException(status_code=403, detail="Forbidden")


def _cors_allow_origin_list() -> list[str]:
    origins = settings.web_cors_origin_list()
    if origins == ["*"]:
        # Explicit list preferred for credentialed-free public widget
        return [
            "https://bots.krivoshein.site",
            "https://wordpress.krivoshein.site",
            "https://vps.krivoshein.site",
            "https://direct.krivoshein.site",
            "https://landing.krivoshein.site",
            "https://ai-ready.krivoshein.site",
            "https://krivoshein.site",
            "https://www.krivoshein.site",
            "https://support.krivoshein.site",
        ]
    return origins


@asynccontextmanager
async def lifespan(application: FastAPI):
    setup_logging(settings.log_level)
    client = MaxApiClient(settings.max_bot_token)
    db = await connect_db(settings.database_path)
    try:
        await init_db(db)
        bot = await client.get_me()
        logger.info("Бот подключён: %s (user_id=%s)", bot.name, bot.user_id)
    except MaxApiError as exc:
        await client.aclose()
        await db.close()
        logger.error("Не удалось проверить MAX API при старте: %s", exc)
        raise RuntimeError("MAX API token check failed") from exc

    chat_memory = ChatMemory(db)
    llm_service = LlmService(memory=chat_memory)
    application.state.db = db
    application.state.max_client = client
    application.state.chat_memory = chat_memory
    application.state.llm_service = llm_service
    application.state.router = BotRouter(
        client,
        TicketStorage(db),
        llm_service=llm_service,
        chat_memory=chat_memory,
    )

    # Web AI assistant
    web_store = WebStore(db)
    await web_store.init()
    knowledge = KnowledgeLoader(
        hub_llms_path=settings.web_hub_llms_path,
        sites_root=settings.web_sites_root,
        ttl_seconds=settings.web_knowledge_ttl_seconds,
    )
    web_assistant = WebAssistantService(
        web_store,
        max_client=client,
        knowledge=knowledge,
    )
    application.state.web_store = web_store
    application.state.web_assistant = web_assistant
    application.state.knowledge = knowledge
    logger.info(
        "Web assistant enabled=%s cors=%s",
        settings.web_assistant_enabled,
        len(_cors_allow_origin_list()),
    )

    yield

    await web_assistant.aclose()
    await llm_service.aclose()
    await client.aclose()
    await db.close()


def create_app() -> FastAPI:
    application = FastAPI(title="Krivoshein Code Support", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origin_list(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
        max_age=600,
    )

    application.include_router(web_router)

    @application.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "web_assistant": settings.web_assistant_enabled,
        }

    @application.post(settings.webhook_path)
    async def receive_update(request: Request) -> dict[str, bool]:
        _verify_webhook_secret(request)

        try:
            update = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

        if not isinstance(update, dict):
            raise HTTPException(status_code=400, detail="Update must be a JSON object")

        router: BotRouter = request.app.state.router
        update_type = update.get("update_type", "unknown")
        chat_id = update.get("chat_id")
        try:
            await router.handle_update(update)
        except MaxApiError:
            logger.exception(
                "Ошибка MAX API при обработке апдейта: update_type=%s, chat_id=%s",
                update_type,
                chat_id,
            )
        except Exception:
            logger.exception(
                "Непредвиденная ошибка при обработке апдейта: update_type=%s, chat_id=%s",
                update_type,
                chat_id,
            )
        return {"ok": True}

    return application


app = create_app()
