"""Register MAX webhook subscription.

Manual registration (one-time or after URL change):

    cd /opt/krivoshein-code-support
    source venv/bin/activate
    python -m scripts.register_webhook

Requires MAX_BOT_TOKEN, WEBHOOK_URL and WEBHOOK_SECRET in .env.
The public URL must be reachable over HTTPS on port 443.
After adding or changing WEBHOOK_SECRET, re-run this script so MAX sends
X-Max-Bot-Api-Secret on every webhook delivery.

Alternative via curl:

    curl -X POST "https://platform-api.max.ru/subscriptions" \\
      -H "Authorization: $MAX_BOT_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{
        "url": "https://support.krivoshein.site/webhook",
        "update_types": ["bot_started", "message_created", "message_callback"],
        "secret": "$WEBHOOK_SECRET"
      }'
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.config import settings
from app.logging_config import setup_logging
from app.max_api import MaxApiClient
from app.max_api.exceptions import MaxApiError

logger = logging.getLogger(__name__)

DEFAULT_UPDATE_TYPES = [
    "bot_started",
    "message_created",
    "message_callback",
]


def _print_subscriptions(payload: dict) -> None:
    subscriptions = payload.get("subscriptions", [])
    if not subscriptions:
        print("Подписки не найдены.")
        return

    print("Текущие подписки:")
    print(json.dumps(subscriptions, ensure_ascii=False, indent=2))


async def run() -> int:
    setup_logging(settings.log_level)

    if not settings.max_bot_token:
        logger.error("MAX_BOT_TOKEN не найден в .env")
        return 1

    if not settings.webhook_url:
        logger.error("WEBHOOK_URL не задан")
        return 1

    if not settings.webhook_secret:
        logger.error("WEBHOOK_SECRET не задан")
        return 1

    client = MaxApiClient(settings.max_bot_token)
    try:
        bot = await client.get_me()
        logger.info("Бот: %s (user_id=%s)", bot.name, bot.user_id)

        print(f"Webhook URL: {settings.webhook_url}")
        print(f"Типы событий: {', '.join(DEFAULT_UPDATE_TYPES)}")
        print(f"Секрет: задан (длина {len(settings.webhook_secret)})")
        print()

        print("=== До регистрации ===")
        before = await client.get_webhook_subscriptions()
        _print_subscriptions(before)
        print()

        result = await client.register_webhook(
            settings.webhook_url,
            DEFAULT_UPDATE_TYPES,
            secret=settings.webhook_secret,
        )
        success = result.get("success")
        message = result.get("message")

        print("=== Результат регистрации ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if success is False:
            logger.error("Регистрация webhook не удалась: %s", message or "unknown error")
            return 1

        print()
        print("=== После регистрации ===")
        after = await client.get_webhook_subscriptions()
        _print_subscriptions(after)
        return 0
    except MaxApiError as exc:
        logger.error("Ошибка MAX API: %s", exc)
        return 1
    finally:
        await client.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()