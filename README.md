# Krivoshein Code Support

Бот поддержки в мессенджере [MAX](https://max.ru): FAQ, приём заявок, уведомления в админ-канал.

## Стек

- Python 3.12
- FastAPI + Uvicorn (webhook)
- httpx (MAX API)
- aiosqlite (сессии заявок)
- pydantic-settings

## Быстрый старт

1. Клонировать репозиторий и создать виртуальное окружение:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Скопировать `.env.example` → `.env` и заполнить переменные:
   - `MAX_BOT_TOKEN` — токен бота MAX
   - `WEBHOOK_SECRET` — секрет webhook (обязательно; 5–256 символов: `A-Z`, `a-z`, `0-9`, `_`, `-`)
   - `ADMIN_CHANNEL_ID` — ID канала для заявок (опционально)
   - `WEBHOOK_URL` — публичный HTTPS-URL webhook

   Сгенерировать секрет для локальной разработки:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Без `WEBHOOK_SECRET` любой, кто знает URL webhook, может слать фейковые апдейты.
   MAX передаёт секрет в заголовке `X-Max-Bot-Api-Secret` при каждой доставке события.

3. Проверить подключение к API:

   ```bash
   python -m app.main
   ```

4. Запустить webhook-сервер:

   ```bash
   uvicorn app.webhook:app --host 127.0.0.1 --port 8000
   ```

5. Зарегистрировать webhook в MAX (один раз после деплоя и при смене `WEBHOOK_SECRET`):

   ```bash
   python -m scripts.register_webhook
   ```

   После добавления или смены секрета перезапустите uvicorn и заново выполните регистрацию —
   иначе MAX не будет слать заголовок `X-Max-Bot-Api-Secret`, и запросы получат `403 Forbidden`.

   Локальная отладка webhook (curl):

   ```bash
   curl -X POST http://127.0.0.1:8000/webhook \
     -H "Content-Type: application/json" \
     -H "X-Max-Bot-Api-Secret: $WEBHOOK_SECRET" \
     -d '{"update_type":"bot_started","chat_id":123}'
   ```

## Деплой

Пример systemd-юнита — `app/webhook.service.example`. После запуска сервиса выполните регистрацию webhook (шаг 5 выше). Публичный URL должен быть доступен по HTTPS на порту 443 (прокси перед uvicorn). `WEBHOOK_SECRET` должен быть в `/opt/krivoshein-code-support/.env`.