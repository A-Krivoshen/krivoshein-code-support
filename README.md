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
   - `ADMIN_CHANNEL_ID` — ID канала для заявок (опционально)
   - `WEBHOOK_URL` — публичный HTTPS-URL webhook

3. Проверить подключение к API:

   ```bash
   python -m app.main
   ```

4. Запустить webhook-сервер:

   ```bash
   uvicorn app.webhook:app --host 127.0.0.1 --port 8000
   ```

5. Зарегистрировать webhook в MAX (один раз после деплоя):

   ```bash
   python -m scripts.register_webhook
   ```

## Деплой

Пример systemd-юнита — `app/webhook.service.example`. После запуска сервиса выполните регистрацию webhook (шаг 5 выше). Публичный URL должен быть доступен по HTTPS на порту 443 (прокси перед uvicorn).