from __future__ import annotations

import json
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from app.bot.router import BotRouter
from app.config import settings
from app.db import connect_db, init_db
from app.logging_config import setup_logging
from app.max_api import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.tickets.storage import TicketStorage

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

    application.state.db = db
    application.state.max_client = client
    application.state.router = BotRouter(client, TicketStorage(db))
    yield
    await client.aclose()
    await db.close()


def create_app() -> FastAPI:
    application = FastAPI(title="Krivoshein Code Support", lifespan=lifespan)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

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
        try:
            await router.handle_update(update)
        except Exception:
            logger.exception("Ошибка обработки апдейта: update_type=%s", update.get("update_type"))
        return {"ok": True}

    return application


app = create_app()