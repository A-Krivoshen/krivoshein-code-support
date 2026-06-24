import asyncio
import logging

from app.config import settings
from app.logging_config import setup_logging
from app.max_api import MaxApiClient
from app.max_api.exceptions import MaxApiError


async def run() -> None:
    """Точка входа для проверки подключения к MAX API."""
    setup_logging(settings.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Запуск проверки подключения...")

    if not settings.max_bot_token:
        logger.error("MAX_BOT_TOKEN не найден в .env!")
        return

    logger.info(f"Токен MAX загружен (длина: {len(settings.max_bot_token)})")

    client = MaxApiClient(settings.max_bot_token)
    try:
        bot = await client.get_me()
        logger.info("Бот подключён: %s (user_id=%s)", bot.name, bot.user_id)
        logger.info("Клиент MAX API успешно проверен")
    except MaxApiError as exc:
        logger.error("Не удалось проверить MAX API: %s", exc)
    finally:
        await client.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()