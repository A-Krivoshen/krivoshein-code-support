# Web AI Popup Assistant

Единый лёгкий чат-виджет для лендингов и (позже) главного сайта.  
Backend — расширение **krivoshein-code-support** (тот же uvicorn `:8080`).

## Возможности MVP

- Bubble + popup (vanilla JS/CSS)
- Контекст `hostname` + `pathname`
- Knowledge из локальных `llms.txt` (хаб + текущий лендинг)
- Chat через Groq (`LLM_*` как у MAX-бота)
- Заявка → SQLite + уведомление в **MAX admin channel**
- Handoff: Telegram @DrSlon, MAX, contacts, прайс
- Rate-limit, honeypot, CORS allowlist

## API

Base: `https://support.krivoshein.site`

| Method | Path | Body |
|--------|------|------|
| POST | `/api/v1/bootstrap` | `{ host, path, session_id? }` |
| POST | `/api/v1/chat` | `{ session_id, host, path, message, website? }` |
| POST | `/api/v1/lead` | `{ session_id, host, path, topic?, need, budget?, urgency?, contact, website? }` |
| GET | `/widget/krv-assistant.js` | — |
| GET | `/widget/krv-assistant.css` | — |
| GET | `/health` | `{ status, web_assistant }` |

`website` — honeypot (должен быть пустым).

## Embed

```html
<script src="https://support.krivoshein.site/widget/krv-assistant.js?v=YYYYMMDD"
  defer
  data-api="https://support.krivoshein.site/api/v1"
  data-side="left"></script>
```

- `data-side="left"` — слева (Replain обычно справа)
- `data-side="right"` — справа

## Env

См. `.env.example`:

- `WEB_ASSISTANT_ENABLED=true`
- `WEB_CORS_ORIGINS=...` (comma-separated)
- `WEB_RATE_LIMIT_PER_HOUR=30`
- `WEB_HUB_LLMS_PATH=/var/www/krivoshein.site/htdocs/llms.txt`
- `WEB_SITES_ROOT=/var/www`
- `WEB_KNOWLEDGE_TTL_SECONDS=600`

Нужны также `LLM_ENABLED`, `LLM_API_KEY`, `ADMIN_CHANNEL_ID`.

## Deploy

```bash
cd /opt/krivoshein-code-support
# code already on server
systemctl restart krivoshein-code-support.service
systemctl status krivoshein-code-support.service --no-pager
curl -sS https://support.krivoshein.site/health
```

Nginx (`support.krivoshein.site`): locations `/api/`, `/widget/`, `/health` → `127.0.0.1:8080`.  
Бэкап конфига: `/etc/nginx/sites-enabled/support.krivoshein.site.bak-*`

## Тест: bots.krivoshein.site

Виджет добавлен **слева**, Replain **не отключался**.

Проверка:

1. Открыть https://bots.krivoshein.site/ (hard refresh)
2. Слева внизу — синий bubble
3. Приветствие про ботов, quick-replies
4. Вопрос про цену → ориентир «от 40 000 ₽»
5. «Оставить заявку» → сообщение в MAX admin

## Раскатка (план)

1. `wordpress` / `vps` / `direct` / `landing` / `ai-ready` — та же одна строка script
2. Главный WP — enqueue script + убрать Replain из GDPR third-party
3. После стабилизации — выключить Replain на лендингах

## Код

```
app/web/
  knowledge.py   # llms.txt loader + profiles
  store.py       # SQLite web_* tables
  service.py     # chat + lead
  router.py      # /api/v1/* + /widget/*
  schemas.py
  static/krv-assistant.js
  static/krv-assistant.css
```

## Proactive invite

After ~50s of idle (62s on viewports &lt; 480px) shows a soft tip next to the bubble with a site-specific question.
- Dismiss (×) → `localStorage.krv_assistant_proactive_dismissed=1` (session never again)
- Shown once per tab → `sessionStorage.krv_assistant_proactive_shown=1`
- Does not open the full panel; click tip/bubble opens chat as usual
- Suppressed while the panel is open
