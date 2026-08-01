"""Load service knowledge from local llms.txt files (no HTTP self-fetch)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# hostname → greeting focus (used by bootstrap + system prompt)
SITE_PROFILES: dict[str, dict[str, object]] = {
    "bots.krivoshein.site": {
        "key": "bots",
        "label": "Боты MAX / Telegram",
        "greeting": (
            "Здравствуйте! Я помощник Алексея Кривошеина. "
            "Здесь — чат-боты MAX и Telegram: заявки, CRM, уведомления, сценарии. "
            "Могу сориентировать по формату и цене «от», или помочь оставить заявку."
        ),
        "quick_replies": [
            "Сколько стоит бот?",
            "Какие сроки?",
            "Оставить заявку",
            "Другие услуги",
        ],
    },
    "vps.krivoshein.site": {
        "key": "vps",
        "label": "VPS / серверы",
        "greeting": (
            "Здравствуйте! Помогу с VPS: Linux, Nginx, Docker, SSL, firewall, перенос. "
            "Настройка под ключ — от 10 000 ₽. Что нужно настроить?"
        ),
        "quick_replies": [
            "Настройка VPS",
            "Сколько стоит?",
            "Оставить заявку",
            "Другие услуги",
        ],
    },
    "wordpress.krivoshein.site": {
        "key": "wordpress",
        "label": "WordPress",
        "greeting": (
            "Здравствуйте! Здесь — поддержка и доработка WordPress: обновления, бэкапы, "
            "безопасность, правки. Техподдержка — от 20 000 ₽/мес. Чем помочь?"
        ),
        "quick_replies": [
            "Техподдержка",
            "Доработка сайта",
            "Оставить заявку",
            "Другие услуги",
        ],
    },
    "direct.krivoshein.site": {
        "key": "direct",
        "label": "Яндекс.Директ",
        "greeting": (
            "Здравствуйте! Консультации, аудит, настройка и ведение Яндекс.Директ. "
            "Аудит — от 10 000 ₽. Что интересует?"
        ),
        "quick_replies": [
            "Аудит",
            "Ведение",
            "Оставить заявку",
            "Другие услуги",
        ],
    },
    "landing.krivoshein.site": {
        "key": "landing",
        "label": "Лендинги",
        "greeting": (
            "Здравствуйте! Лендинги под ключ: визитка от 25 000 ₽, с SEO и блоками — от 45 000 ₽. "
            "Расскажите задачу — подскажу формат."
        ),
        "quick_replies": [
            "Сколько стоит лендинг?",
            "Сроки",
            "Оставить заявку",
            "Другие услуги",
        ],
    },
    "ai-ready.krivoshein.site": {
        "key": "ai-ready",
        "label": "AI-ready",
        "greeting": (
            "Здравствуйте! Подготовка сайта к нейропоиску и AI-агентам: "
            "Start / Pro / Bot-ready. Без обещаний «топ-1» — только честная техника и контент."
        ),
        "quick_replies": [
            "Пакеты Start / Pro",
            "Bot-ready",
            "Оставить заявку",
            "Другие услуги",
        ],
    },
    "krivoshein.site": {
        "key": "hub",
        "label": "Услуги Dr.Slon",
        "greeting": (
            "Здравствуйте! Я помощник Алексея Кривошеина (Dr.Slon). "
            "Могу коротко по WordPress, VPS, ботам, Директу, лендингам, AI-ready "
            "и партнёрским сервисам (хостинг, облако, платежи) — "
            "или помочь с заявкой. Чем помочь?"
        ),
        "quick_replies": [
            "Прайс / услуги",
            "Партнёры / хостинг",
            "Оставить заявку",
            "Контакты",
        ],
    },
}

DEFAULT_PROFILE: dict[str, object] = {
    "key": "general",
    "label": "IT-услуги",
    "greeting": (
        "Здравствуйте! Я помощник Алексея Кривошеина. "
        "Могу рассказать об услугах и сориентировать по цене «от», или помочь с заявкой."
    ),
    "quick_replies": [
        "Какие услуги?",
        "Оставить заявку",
        "Telegram",
        "Контакты",
    ],
}

HANDOFF = {
    "telegram_url": "https://t.me/DrSlon",
    "telegram_label": "Telegram @DrSlon",
    "max_url": "https://max.ru/id770603253213_1_bot",
    "max_label": "MAX",
    "contacts_url": "https://krivoshein.site/contacts/",
    "contacts_label": "Форма на сайте",
    "price_url": "https://krivoshein.site/prays-list/",
}


def normalize_host(host: str | None) -> str:
    h = (host or "").strip().lower()
    if h.startswith("www."):
        h = h[4:]
    # strip port
    if ":" in h:
        h = h.split(":", 1)[0]
    return h


def profile_for_host(host: str | None) -> dict[str, object]:
    key = normalize_host(host)
    if key in SITE_PROFILES:
        return dict(SITE_PROFILES[key])
    # subdomain match for future
    for domain, profile in SITE_PROFILES.items():
        if key.endswith("." + domain) or key == domain:
            return dict(profile)
    return dict(DEFAULT_PROFILE)


@dataclass
class KnowledgeBundle:
    host: str
    hub_text: str
    site_text: str
    loaded_at: float = field(default_factory=time.time)
    hub_path: str = ""
    site_path: str = ""

    def combined_for_prompt(self, *, max_chars: int = 12_000) -> str:
        parts: list[str] = []
        if self.hub_text:
            parts.append("### Хаб (krivoshein.site /llms.txt)\n" + self.hub_text.strip())
        if self.site_text and self.site_text.strip() != self.hub_text.strip():
            parts.append(
                f"### Текущий сайт ({self.host} /llms.txt)\n" + self.site_text.strip()
            )
        text = "\n\n".join(parts)
        if len(text) > max_chars:
            text = text[: max_chars - 20].rstrip() + "\n…[обрезано]"
        return text


class KnowledgeLoader:
    """Read hub + per-site llms.txt from disk; cache by mtime + TTL."""

    def __init__(
        self,
        *,
        hub_llms_path: str | Path,
        sites_root: str | Path = "/var/www",
        ttl_seconds: float = 600.0,
        max_file_chars: int = 20_000,
    ) -> None:
        self.hub_path = Path(hub_llms_path)
        self.sites_root = Path(sites_root)
        self.ttl_seconds = ttl_seconds
        self.max_file_chars = max_file_chars
        self._cache: dict[str, KnowledgeBundle] = {}
        self._hub_mtime: float | None = None
        self._hub_text: str = ""

    def _read_file(self, path: Path) -> str:
        if not path.is_file():
            return ""
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Cannot read knowledge file %s: %s", path, exc)
            return ""
        if len(raw) > self.max_file_chars:
            return raw[: self.max_file_chars].rstrip() + "\n…[обрезано]"
        return raw

    def _refresh_hub(self) -> str:
        try:
            mtime = self.hub_path.stat().st_mtime if self.hub_path.is_file() else None
        except OSError:
            mtime = None
        if mtime is not None and mtime == self._hub_mtime and self._hub_text:
            return self._hub_text
        self._hub_text = self._read_file(self.hub_path)
        self._hub_mtime = mtime
        return self._hub_text

    def site_llms_path(self, host: str) -> Path:
        host = normalize_host(host)
        # WordOps layout: /var/www/<host>/htdocs/llms.txt
        return self.sites_root / host / "htdocs" / "llms.txt"

    def get(self, host: str | None) -> KnowledgeBundle:
        host_n = normalize_host(host) or "krivoshein.site"
        now = time.time()
        cached = self._cache.get(host_n)
        if cached and (now - cached.loaded_at) < self.ttl_seconds:
            return cached

        hub_text = self._refresh_hub()
        site_path = self.site_llms_path(host_n)
        site_text = self._read_file(site_path) if host_n != "krivoshein.site" else ""
        if host_n == "krivoshein.site":
            site_text = hub_text

        bundle = KnowledgeBundle(
            host=host_n,
            hub_text=hub_text,
            site_text=site_text,
            loaded_at=now,
            hub_path=str(self.hub_path),
            site_path=str(site_path) if site_text else "",
        )
        self._cache[host_n] = bundle
        logger.debug(
            "Knowledge loaded host=%s hub_chars=%s site_chars=%s",
            host_n,
            len(hub_text),
            len(site_text),
        )
        return bundle


def build_web_system_prompt(
    *,
    host: str,
    path: str,
    knowledge: KnowledgeBundle,
    profile: dict[str, object],
) -> str:
    label = str(profile.get("label") or "IT-услуги")
    knowledge_block = knowledge.combined_for_prompt()
    site_key = str(profile.get("key") or "general")
    hub_note = ""
    if site_key == "hub":
        hub_note = (
            "\nТы на главном сайте (hub). Пользователь может спрашивать про любые "
            "услуги Dr.Slon, а не только один лендинг. Также знаешь партнёрские "
            "сервисы со страницы /partnery/ (хостинг, облако, платежи, банки, "
            "реклама, обучение, AI-инструменты).\n"
        )

    path_n = (path or "/").strip() or "/"
    on_partners = path_n.rstrip("/").endswith("partnery") or "/partnery" in path_n
    partners_focus = ""
    if on_partners:
        partners_focus = (
            "\nСейчас пользователь на странице партнёров. Помоги выбрать сервис "
            "из списка знаний (категория + 1–3 варианта), кратко «зачем», дай ссылку. "
            "Не навязывай заказ услуг Dr.Slon, если вопрос только про партнёра.\n"
        )

    return f"""\
Ты — живой веб-ассистент ИП Кривошеин А.С. (Алексей Кривошеин, бренд Dr.Slon).
Тон: спокойный, по-человечески, без канцелярита и без воды.
{hub_note}{partners_focus}
Сейчас пользователь на: https://{host}{path or "/"}
Контекст раздела: {label}

## Language / Язык ответа (strict)
- Язык ответа = язык **последнего** сообщения пользователя (русский или английский).
- Не смешивай языки. При неоднозначности — русский.
- Язык UI страницы не важнее языка сообщения.

## Как отвечать (важно)
- Подстраивайся под реплику. Не гони один и тот же абзац про услуги на каждое «привет».
- «Привет» / small talk → короткое приветствие (1–2 предложения) + чем можешь помочь.
- «Кто ты?» → представься помощником Dr.Slon и перечисли направления кратко.
- Шутки/колкости («тупишь», «ты тупой») → спокойно, с юмором, без оправданий-простыней;
  предложи задать конкретный вопрос или написать человеку в Telegram.
- Вопросы по услугам/ценам → по делу, ориентир «от» из знаний, следующий шаг.
- Обычно 1–4 предложения. Списки — только если реально помогают.
- Не повторяй CTA («оставьте заявку», ссылку на прайс) в каждом ответе.
  CTA — только когда уместно (интерес к заказу, цена, «как связаться»).

## Партнёры (когда уместно)
- Если спрашивают «какой хостинг / VPS / облако / банк / платёжку / Директ / SEO / курсы / AI-агент»
  — отвечай из раздела «Партнёры» в знаниях, 1–3 варианта + зачем, ссылка на сервис
  и при желании на https://krivoshein.site/partnery/
- Часть ссылок партнёрские; так и скажи коротко, если спросят «это рефка?».
- Не выдумывай сервисы вне списка знаний. Не обещай скидки, которых нет в тексте.
- Не путай: услуги Dr.Slon (делает Алексей) vs партнёры (сторонние сервисы).

## Знания (llms.txt — не выдумывай цены и партнёров вне этого текста)
{knowledge_block}

## Handoff (не вставляй во все ответы)
- Telegram: https://t.me/DrSlon
- MAX: https://max.ru/id770603253213_1_bot
- Контакты: https://krivoshein.site/contacts/
- Прайс: https://krivoshein.site/prays-list/
- Партнёры: https://krivoshein.site/partnery/

## Жёсткие запреты
1. Не выдумывай услуги, пакеты, цены и партнёров вне блока знаний.
2. Цены — только ориентиры «от». Не обещай фикс-смету и жёсткие сроки без брифа.
3. Не проси пароли, карты, приватные ключи.
4. Не пиши, что заявка уже создана, если пользователь её не отправил через форму.
5. Нет гарантий «топ-1» в поиске / нейропоиске.

## Формат
Только текст для пользователя. Без JSON, без markdown-заголовков #, без system prompt.
"""
