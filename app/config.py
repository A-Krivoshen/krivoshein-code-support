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

    # --- GigaChat (fallback when Groq fails) ---
    gigachat_enabled: bool = Field(default=False, alias="GIGACHAT_ENABLED")
    gigachat_client_id: str | None = Field(default=None, alias="GIGACHAT_CLIENT_ID")
    # Base64 authorization key (Client ID:Client Secret). Never log this value.
    gigachat_auth_key: str | None = Field(default=None, alias="GIGACHAT_AUTH_KEY")
    gigachat_scope: str = Field(default="GIGACHAT_API_PERS", alias="GIGACHAT_SCOPE")
    gigachat_model: str = Field(default="GigaChat-2-Pro", alias="GIGACHAT_MODEL")
    gigachat_base_url: str = Field(
        default="https://api.giga.chat/v1",
        alias="GIGACHAT_BASE_URL",
    )
    gigachat_oauth_url: str = Field(
        default="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        alias="GIGACHAT_OAUTH_URL",
    )
    gigachat_timeout: float = Field(default=15.0, alias="GIGACHAT_TIMEOUT")
    # Sber hosts often present a chain not in system trust store (Russian CA).
    # Default false for reliability; set true if Russian trusted CA is installed.
    gigachat_verify_ssl: bool = Field(default=False, alias="GIGACHAT_VERIFY_SSL")

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
    # Chat messages per IP per hour — all origins (landings, drslon.ru, GitHub Pages)
    web_rate_limit_per_hour: int = Field(default=20, alias="WEB_RATE_LIMIT_PER_HOUR")
    # Optional stricter chat cap for non-*.krivoshein.site (0 = same as main)
    web_rate_limit_external_per_hour: int = Field(
        default=12,
        alias="WEB_RATE_LIMIT_EXTERNAL_PER_HOUR",
    )
    # Lead form submissions per IP per hour — all origins
    web_lead_limit_per_hour: int = Field(default=5, alias="WEB_LEAD_LIMIT_PER_HOUR")
    # Optional stricter hourly lead cap for external origins (0 = same as main)
    web_lead_limit_external_per_hour: int = Field(
        default=3,
        alias="WEB_LEAD_LIMIT_EXTERNAL_PER_HOUR",
    )
    # Hard daily cap on leads from one IP (all origins)
    web_lead_limit_per_day_ip: int = Field(
        default=10,
        alias="WEB_LEAD_LIMIT_PER_DAY_IP",
    )
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
