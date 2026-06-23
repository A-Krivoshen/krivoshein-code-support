import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Настройка логирования для Grok Builder"""

    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Отключаем лишние логи от библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
