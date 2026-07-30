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
    # Секрет webhook: MAX шлёт его в X-Max-Bot-Api-Secret при каждом POST.
    # Без проверки любой, кто знает URL, может отправлять фейковые апдейты.
    webhook_secret: str = Field(
        ...,
        alias="WEBHOOK_SECRET",
        min_length=5,
        max_length=256,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )

    # --- LLM (Groq) ---
    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        alias="LLM_BASE_URL",
    )
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="LLM_MODEL",
    )
    llm_timeout: float = Field(default=10.0, alias="LLM_TIMEOUT")
    llm_max_tokens: int = Field(default=500, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    # Лимит вызовов LLM на chat_id за скользящий час
    llm_rate_limit_per_hour: int = Field(default=8, alias="LLM_RATE_LIMIT_PER_HOUR")
    # Сколько пар user+assistant держать в контексте
    llm_history_pairs: int = Field(default=5, alias="LLM_HISTORY_PAIRS")
    # TTL истории диалога (часы)
    llm_history_ttl_hours: int = Field(default=24, alias="LLM_HISTORY_TTL_HOURS")

    # --- Web AI Popup Assistant ---
    web_assistant_enabled: bool = Field(default=True, alias="WEB_ASSISTANT_ENABLED")
    # Comma-separated origins. Empty or * → allow *.krivoshein.site
    web_cors_origins: str = Field(
        default=(
            "https://bots.krivoshein.site,"
            "https://wordpress.krivoshein.site,"
            "https://vps.krivoshein.site,"
            "https://direct.krivoshein.site,"
            "https://landing.krivoshein.site,"
            "https://ai-ready.krivoshein.site,"
            "https://krivoshein.site,"
            "https://www.krivoshein.site,"
            "https://support.krivoshein.site,"
            "https://drslon.ru,"
            "https://a-krivoshen.github.io"
        ),
        alias="WEB_CORS_ORIGINS",
    )
    web_rate_limit_per_hour: int = Field(default=30, alias="WEB_RATE_LIMIT_PER_HOUR")
    web_hub_llms_path: str = Field(
        default="/var/www/krivoshein.site/htdocs/llms.txt",
        alias="WEB_HUB_LLMS_PATH",
    )
    web_sites_root: str = Field(default="/var/www", alias="WEB_SITES_ROOT")
    web_knowledge_ttl_seconds: float = Field(
        default=600.0,
        alias="WEB_KNOWLEDGE_TTL_SECONDS",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def web_cors_origin_list(self) -> list[str]:
        raw = (self.web_cors_origins or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [part.strip().rstrip("/") for part in raw.split(",") if part.strip()]


settings = Settings()
