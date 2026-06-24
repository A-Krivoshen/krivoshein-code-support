from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения."""

    # MAX Bot
    max_bot_token: str = Field(..., alias="MAX_BOT_TOKEN")

    # База данных
    database_path: str = Field(default="data/bot.sqlite3", alias="DATABASE_PATH")

    # Логирование
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Админ (для уведомлений)
    admin_channel_id: int | None = Field(default=None, alias="ADMIN_CHANNEL_ID")

    # Webhook
    webhook_path: str = Field(default="/webhook", alias="WEBHOOK_PATH")
    webhook_url: str = Field(
        default="https://support.krivoshein.site/webhook",
        alias="WEBHOOK_URL",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()