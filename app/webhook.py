from __future__ import annotations

import json
import logging
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