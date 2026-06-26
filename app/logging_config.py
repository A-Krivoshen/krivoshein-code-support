import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Настройка логирования приложения."""

    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )
    else:
        root.setLevel(log_level)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)