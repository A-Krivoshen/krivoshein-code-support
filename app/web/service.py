"""Business logic for web chat + lead handoff to MAX admin channel."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from app.config import Settings, settings
from app.llm.client import LlmClient, LlmError
from app.max_api import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.web.knowledge import (
    HANDOFF,
    KnowledgeLoader,
    build_web_system_prompt,
    normalize_host,
    profile_for_host,
)
from app.web.store import WebStore

logger = logging.getLogger(__name__)

# Heuristic: user is ready to leave a lead
_LEAD_HINT = re.compile(
    r"(заявк|свяжит|напиши|позвон|смета|нужен бот|нужна поддержка|"
    r"хочу заказать|оформить|оставить контакт|перезвон)",
    re.I,
)


def new_session_id() -> str:
    return uuid.uuid4().hex


def is_valid_session_id(value: str | None) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"[a-f0-9]{16,64}", value.strip().lower()))


def handoff_payload() -> dict[str, str]:
    return dict(HANDOFF)



def _looks_english(text: str) -> bool:
    """Heuristic: mostly Latin letters → English."""
    letters = [c for c in (text or "") if c.isalpha()]
    if len(letters) < 3:
        return False
    latin = sum(1 for c in letters if ("a" <= c.lower() <= "z"))
    return (latin / len(letters)) >= 0.6


def _host_from_originish(value: str | None) -> str:
    """Extract bare hostname from Origin header or host field."""
    raw = (value or "").strip()
    if not raw:
        return ""
    from urllib.parse import urlparse

    if "://" in raw:
        try:
            return normalize_host(urlparse(raw).netloc or "")
        except Exception:
            return ""
    return normalize_host(raw)


def is_own_ecosystem_origin(origin: str | None, host: str | None = None) -> bool:
    """True for krivoshein.site / *.krivoshein.site (landings + hub).

    External public embeds (drslon.ru, GitHub Pages, …) get stricter limits.
    """
    for raw in (origin, host):
        h = _host_from_originish(raw)
        if not h:
            continue
        if h == "krivoshein.site" or h.endswith(".krivoshein.site"):
            return True
    return False


class WebAssistantService:
    def __init__(
        self,
        store: WebStore,
        *,
        max_client: MaxApiClient | None = None,
        llm_client: LlmClient | None = None,
        knowledge: KnowledgeLoader | None = None,
        config: Settings | None = None,
    ) -> None:
        self._store = store
        self._settings = config or settings
        self._max = max_client
        self._llm = llm_client or LlmClient(self._settings)
        self._owns_llm = llm_client is None
        self._knowledge = knowledge or KnowledgeLoader(
            hub_llms_path=self._settings.web_hub_llms_path,
            sites_root=self._settings.web_sites_root,
            ttl_seconds=self._settings.web_knowledge_ttl_seconds,
        )

    async def aclose(self) -> None:
        if self._owns_llm:
            await self._llm.aclose()

    async def bootstrap(
        self,
        *,
        host: str,
        path: str,
        session_id: str | None,
    ) -> dict:
        host_n = normalize_host(host)
        path_n = path or "/"
        profile = profile_for_host(host_n)
        sid = (
            session_id.strip().lower()
            if is_valid_session_id(session_id)
            else new_session_id()
        )
        await self._store.touch_session(sid, host=host_n, path=path_n)
        return {
            "session_id": sid,
            "host": host_n,
            "site_key": str(profile.get("key") or "general"),
            "site_label": str(profile.get("label") or "IT-услуги"),
            "greeting": str(profile.get("greeting") or ""),
            "quick_replies": list(profile.get("quick_replies") or []),
            "handoff": handoff_payload(),
            "title": "Помощник Dr.Slon",
            "subtitle": str(profile.get("label") or "Услуги и заявки"),
            "path": path_n,
        }

    async def chat(
        self,
        *,
        session_id: str,
        host: str,
        path: str,
        message: str,
        client_ip: str,
        honeypot: str = "",
        origin: str | None = None,
    ) -> dict:
        if honeypot.strip():
            # silent success for bots — no chat recorded
            logger.info(
                "Web rate/honeypot endpoint=chat reason=honeypot ip=%s origin=%s host=%s",
                client_ip,
                origin or "",
                host,
            )
            return {
                "session_id": session_id,
                "reply": "Спасибо! Если вопрос срочный — напишите в Telegram @DrSlon.",
                "suggest_lead": False,
                "quick_replies": [],
            }

        host_n = normalize_host(host)
        path_n = path or "/"
        rate_key = f"ip:{client_ip}"
        own = is_own_ecosystem_origin(origin, host_n)
        # All origins get a hard hourly chat cap; external can be stricter.
        limit = self._settings.web_rate_limit_per_hour
        ext = self._settings.web_rate_limit_external_per_hour
        if not own and ext > 0:
            limit = min(limit, ext)

        if await self._store.is_rate_limited(
            rate_key, kind="chat", limit=limit, window_hours=1.0
        ):
            logger.warning(
                "Web rate/limit endpoint=chat reason=hourly_limit ip=%s origin=%s "
                "host=%s limit=%s",
                client_ip,
                origin or "",
                host_n,
                limit,
            )
            en = _looks_english(message)
            return {
                "session_id": session_id,
                "reply": (
                    "Too many messages in a short time. Please wait a bit and try again."
                    if en
                    else (
                        "Слишком много сообщений за короткое время. "
                        "Подождите немного и напишите снова."
                    )
                ),
                "suggest_lead": False,
                "quick_replies": [],
            }

        await self._store.touch_session(session_id, host=host_n, path=path_n)
        await self._store.record_rate(rate_key, kind="chat")
        await self._store.record_rate(f"sess:{session_id}", kind="chat")

        profile = profile_for_host(host_n)
        knowledge = self._knowledge.get(host_n)
        system_prompt = build_web_system_prompt(
            host=host_n,
            path=path_n,
            knowledge=knowledge,
            profile=profile,
        )
        user_en = _looks_english(message)
        # Hard language lock for this turn (models otherwise follow RU knowledge tone)
        if user_en:
            system_prompt += (
                "\n\n## MANDATORY LANGUAGE FOR THIS REPLY (override all above)\n"
                "The user's LATEST message is in ENGLISH.\n"
                "- Answer 100% in English only.\n"
                "- Do NOT write Russian sentences or Russian UI phrases.\n"
                "- Allowed Russian only inside proper names (Dr.Slon, Кривошеин) and URLs.\n"
                "- Prices: keep numbers and ₽; describe them in English "
                "(e.g. \"from 40,000 ₽\").\n"
                "- Ignore that knowledge text / history may be Russian — translate facts to English.\n"
            )
        else:
            system_prompt += (
                "\n\n## MANDATORY LANGUAGE FOR THIS REPLY (override all above)\n"
                "Последнее сообщение пользователя на русском.\n"
                "- Отвечай полностью на русском.\n"
                "- Не смешивай с английским (кроме URL и названий).\n"
            )

        history = await self._store.get_recent_messages(
            session_id,
            max_messages=max(0, self._settings.llm_history_pairs * 2),
            ttl_hours=self._settings.llm_history_ttl_hours,
        )

        reply_text: str | None = None
        if self._settings.llm_enabled and self._settings.llm_api_key:
            messages = [{"role": "system", "content": system_prompt}]
            for item in history:
                if item.get("role") in {"user", "assistant"} and item.get("content"):
                    messages.append(
                        {"role": item["role"], "content": item["content"]}
                    )
            # Short in-band cue right on the user turn (helps small models)
            user_content = message
            if user_en:
                user_content = (
                    "[Language: English — reply in English only]\n" + message
                )
            else:
                user_content = (
                    "[Язык: русский — отвечай только на русском]\n" + message
                )
            messages.append({"role": "user", "content": user_content})
            try:
                reply_text = await self._llm.chat(messages)
                provider = getattr(self._llm, "last_provider", None) or "unknown"
                logger.info("Web chat LLM provider=%s session=%s", provider, session_id[:8])
            except LlmError as exc:
                logger.warning("Web LLM failed (after fallbacks): %s", exc)
                reply_text = None
            except Exception:
                logger.exception("Web LLM unexpected error")
                reply_text = None

            # One retry if model ignored language lock
            if reply_text and user_en and not _looks_english(reply_text):
                logger.info("Web LLM reply language mismatch; retrying in English")
                try:
                    retry_messages = [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                "Reply in English only. User asked:\n" + message
                            ),
                        },
                    ]
                    retry = await self._llm.chat(retry_messages)
                    if retry and _looks_english(retry):
                        reply_text = retry
                        provider = getattr(self._llm, "last_provider", None) or "unknown"
                        logger.info(
                            "Web chat LLM provider=%s session=%s (lang-retry)",
                            provider,
                            session_id[:8],
                        )
                except Exception:
                    logger.warning("Web LLM English retry failed", exc_info=True)
            elif reply_text and (not user_en) and _looks_english(reply_text):
                # Rare: EN reply to RU message — retry in Russian
                logger.info("Web LLM reply language mismatch; retrying in Russian")
                try:
                    retry_messages = [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                "Ответь только на русском. Вопрос пользователя:\n"
                                + message
                            ),
                        },
                    ]
                    retry = await self._llm.chat(retry_messages)
                    if retry and not _looks_english(retry):
                        reply_text = retry
                        provider = getattr(self._llm, "last_provider", None) or "unknown"
                        logger.info(
                            "Web chat LLM provider=%s session=%s (lang-retry)",
                            provider,
                            session_id[:8],
                        )
                except Exception:
                    logger.warning("Web LLM Russian retry failed", exc_info=True)
        else:
            reply_text = None

        if not reply_text:
            reply_text = self._fallback_reply(message, profile)
            logger.info(
                "Web chat LLM provider=offline session=%s",
                session_id[:8],
            )

        await self._store.append_message(session_id, "user", message)
        await self._store.append_message(session_id, "assistant", reply_text)
        await self._store.trim_history(
            session_id,
            max_messages=max(0, self._settings.llm_history_pairs * 2),
            ttl_hours=self._settings.llm_history_ttl_hours,
        )

        suggest = bool(_LEAD_HINT.search(message) or _LEAD_HINT.search(reply_text))
        quick = list(profile.get("quick_replies") or [])
        if suggest and "Оставить заявку" not in quick:
            quick = ["Оставить заявку", *quick[:3]]

        return {
            "session_id": session_id,
            "reply": reply_text,
            "suggest_lead": suggest,
            "quick_replies": quick[:5],
        }

    def _fallback_reply(self, message: str, profile: dict) -> str:
        """Deterministic replies when LLM is down (e.g. 429). Keep them short and human."""
        raw = (message or "").strip()
        low = raw.lower()
        # letters/digits only for short-phrase matching
        compact = re.sub(r"[^\w\sа-яё]", " ", low, flags=re.I)
        compact = re.sub(r"\s+", " ", compact).strip()
        label = str(profile.get("label") or "IT-услуги")
        site_key = str(profile.get("key") or "general")
        en = _looks_english(message)

        if en:
            if re.search(
                r"\b(who are you|what are you|your name|who r u)\b", compact
            ) or compact in {"who", "who you"}:
                return (
                    "I'm the on-site assistant for Alexey Krivoshein (Dr.Slon): "
                    "WordPress, VPS, bots, Yandex Direct, landings, AI-ready. "
                    "What do you need help with?"
                )
            if re.search(
                r"\b(hi|hello|hey|good morning|good evening)\b", compact
            ) or compact in {"hi", "hello", "hey"}:
                return "Hi! I'm Dr.Slon's assistant. Ask about a service or leave a lead — how can I help?"
            if re.search(
                r"\b(stupid|dumb|idiot|useless|rubbish|sucks|dumbass)\b", compact
            ) or "туп" in compact:
                return (
                    "Fair point — I can be limited when the AI is busy. "
                    "Message a human on Telegram @DrSlon, or ask a concrete service/price question."
                )
            if any(w in low for w in ("price", "cost", "how much", "pricing")):
                return self._fallback_service_reply(
                    low, label, en=True, price_focus=True
                )
            if any(w in low for w in ("lead", "order", "contact", "hire")):
                return (
                    "Use «Leave a lead» in this chat (task + contact), "
                    "Telegram @DrSlon, or https://krivoshein.site/contacts/"
                )
            svc = self._fallback_service_reply(
                low, label, en=True, price_focus=False
            )
            if svc:
                return svc
            if ("telegram" in low or "@drslon" in low) and "bot" not in low:
                return "Telegram: https://t.me/DrSlon"
            if any(
                w in low
                for w in ("services", "what do you do", "what can you", "offerings")
            ):
                return (
                    "Dr.Slon services (from-prices): WordPress, VPS, MAX/Telegram bots, "
                    "Yandex Direct, landings, AI-ready. Full list: "
                    "https://krivoshein.site/prays-list/ — which one?"
                )
            return (
                "Tell me the task in a sentence (WordPress, VPS, bot, Direct, landing…) — "
                "I'll outline format and “from” pricing. Or write @DrSlon."
            )

        # --- Russian ---
        if re.search(
            r"кто\s+ты|ты\s+кто|представься|как\s+тебя\s+зовут|что\s+ты\s+такое",
            compact,
        ):
            return (
                "Я помощник Алексея Кривошеина (Dr.Slon) на сайте: "
                "WordPress, VPS, боты MAX/Telegram, Директ, лендинги, AI-ready. "
                "Кратко сориентирую по формату и цене «от» или помогу с заявкой. О чём вопрос?"
            )

        if (
            re.match(
                r"^(привет|здравств|добрый\s+(день|вечер|утро)|хай|хелло|hello|hi)\b",
                compact,
            )
            or compact
            in {
                "привет",
                "здравствуйте",
                "здравствуй",
                "добрый день",
                "добрый вечер",
                "доброе утро",
                "хай",
            }
        ):
            if site_key == "hub":
                return (
                    "Привет! Я помощник Dr.Slon. Могу коротко по услугам и ценам «от» "
                    "или помочь оставить заявку. Чем помочь?"
                )
            return (
                f"Привет! Я помощник на странице «{label}». "
                "Спросите по задаче/цене или нажмите «Оставить заявку»."
            )

        if re.search(
            r"туп|глуп|дурак|идиот|беспол|фигн|херн|отстой|не\s+работа",
            compact,
        ):
            return (
                "Понимаю раздражение — иногда отвечаю упрощённо, если нейросеть недоступна. "
                "Напишите человеку в Telegram @DrSlon или задайте конкретный вопрос "
                "(услуга, цена, сроки) — отвечу по делу."
            )

        if re.search(r"как\s+дела|что\s+умеешь|чем\s+можешь|что\s+можешь", compact):
            return (
                "На связи. Умею: сориентировать по услугам Dr.Slon (WordPress, VPS, боты, "
                "Директ, лендинги, AI-ready), подсказать ориентир «от» и помочь с заявкой. "
                "Что нужно?"
            )

        if any(w in low for w in ("цена", "стоим", "прайс", "сколько", "бюджет")):
            return self._fallback_service_reply(low, label, en=False, price_focus=True)

        if any(w in low for w in ("заявк", "заказ", "свяж", "контакт", "перезвон")):
            return (
                "Оставьте заявку кнопкой «Оставить заявку» в этом чате "
                "(задача + контакт), либо Telegram @DrSlon / MAX, "
                "либо https://krivoshein.site/contacts/"
            )

        # Service intents: Директ, лендинги, WP, VPS, боты, AI-ready, SEO…
        service_reply = self._fallback_service_reply(
            low, label, en=False, price_focus=False
        )
        if service_reply:
            return service_reply

        # Pure contact ask for Telegram (not “telegram bot”)
        if re.search(r"(^|\s)(telegram|телеграм|тг)(\s|$)", low) or "@drslon" in low:
            if "бот" not in low:
                return "Telegram: https://t.me/DrSlon"

        # Overview of all services (hub-style)
        if any(
            w in low
            for w in (
                "услуг",
                "чем занима",
                "что делаешь",
                "что предлага",
                "какие работ",
                "направления",
            )
        ):
            return (
                "Услуги Dr.Slon (ориентиры «от»):\n"
                "• WordPress — поддержка от 20 000 ₽/мес, доработки от 5 000 ₽\n"
                "• VPS — настройка от 10 000 ₽\n"
                "• Боты MAX/Telegram — от 40 000 ₽\n"
                "• Яндекс.Директ — аудит от 10 000 ₽, ведение от 25 000 ₽/мес\n"
                "• Лендинги — от 25 000 ₽\n"
                "• AI-ready — Start от 10 000 ₽ / Pro от 20 000 ₽ / Bot-ready от 30 000 ₽\n"
                "Прайс: https://krivoshein.site/prays-list/ · что именно интересует?"
            )

        # Default: short, no repeated service paragraph
        return (
            "Напишите, что нужно, одной фразой — WordPress, VPS, бот, Директ, лендинг "
            "или AI-ready. Подскажу формат и ориентир «от». Или Telegram @DrSlon."
        )

    def _detect_service_key(self, low: str) -> str | None:
        """Map free text to a service bucket (order matters: more specific first)."""
        # Yandex Direct / ads
        if any(
            w in low
            for w in (
                "директ",
                "яндекс.директ",
                "yandex direct",
                "яндекс директ",
                "контекстн",
                "реклам",
                "кампани",
                "объявлен",
            )
        ) or re.search(r"\b(ads|adwords|ppc)\b", low):
            return "direct"
        if any(
            w in low
            for w in (
                "лендинг",
                "landing",
                "посадоч",
                "one-page",
                "one page",
                "одностранич",
            )
        ):
            return "landing"
        if any(
            w in low
            for w in (
                "ai-ready",
                "ai ready",
                "нейропоиск",
                "нейро-поиск",
                "llms.txt",
                "schema.org",
                "bot-ready",
                "bot ready",
            )
        ):
            return "ai-ready"
        if any(
            w in low for w in ("wordpress", "вордпресс", "wp ", "wp-", "cms")
        ) or re.search(r"\bwp\b", low):
            return "wordpress"
        if any(
            w in low
            for w in ("vps", "сервер", "хостинг", "linux", "nginx", "docker", "devops")
        ):
            return "vps"
        if any(
            w in low
            for w in (
                "бот",
                "чат-бот",
                "chatbot",
                "чатбот",
                "max-бот",
                "telegram-бот",
                "телеграм-бот",
            )
        ) or re.search(r"\bbots?\b", low):
            return "bots"
        if any(w in low for w in ("seo", "сео", "мета-тег", "sitemap", "индексац")):
            return "seo"
        if any(
            w in low
            for w in ("диагност", "аудит сайта", "починить сайт", "ремонт сайта")
        ):
            return "site-fix"
        return None

    def _fallback_service_reply(
        self,
        low: str,
        label: str,
        *,
        en: bool,
        price_focus: bool,
    ) -> str | None:
        """Service-specific blurb (Direct, landings, WP, VPS, bots, AI-ready…).

        Returns None if no service keywords matched (caller continues).
        When price_focus and no service key — generic price list pointer.
        """
        key = self._detect_service_key(low)
        if key is None and not price_focus:
            return None

        if en:
            return self._fallback_service_reply_en(key, label, price_focus=price_focus)

        texts = {
            "direct": (
                "Яндекс.Директ: консультация от 2 000 ₽/час, аудит от 10 000 ₽, "
                "настройка от 20 000 ₽, ведение от 25 000 ₽/мес. "
                "Без слива бюджета — по брифу. "
                "https://direct.krivoshein.site/ · прайс: https://krivoshein.site/prays-list/"
            ),
            "landing": (
                "Лендинги: визитка от 25 000 ₽, с SEO и блоками от 45 000 ₽, "
                "на WordPress от 50 000 ₽. "
                "https://landing.krivoshein.site/ · прайс: https://krivoshein.site/prays-list/"
            ),
            "wordpress": (
                "WordPress: доработки от 5 000 ₽, техподдержка от 20 000 ₽/мес, "
                "корп. сайт от 90 000 ₽. "
                "https://wordpress.krivoshein.site/ · прайс: https://krivoshein.site/prays-list/"
            ),
            "vps": (
                "VPS / Linux: настройка под ключ от 10 000 ₽ "
                "(Nginx, PHP/Docker, SSL, firewall, бэкапы). Сам VPS — у провайдера. "
                "https://vps.krivoshein.site/ · прайс: https://krivoshein.site/prays-list/"
            ),
            "bots": (
                "Боты MAX/Telegram: простой под заявки от 40 000 ₽, "
                "с CRM/таблицами от 70 000 ₽, сопровождение от 5 000 ₽/мес. "
                "https://bots.krivoshein.site/ · прайс: https://krivoshein.site/prays-list/"
            ),
            "ai-ready": (
                "AI-ready (нейропоиск / агенты): Start от 10 000 ₽, Pro от 20 000 ₽, "
                "Bot-ready от 30 000 ₽. Без обещаний «топ-1» — техника и контент. "
                "https://ai-ready.krivoshein.site/ · прайс: https://krivoshein.site/prays-list/"
            ),
            "seo": (
                "Техническое SEO и подготовка к поиску/нейропоиску — в рамках AI-ready "
                "и доработок сайта. Ориентиры: https://ai-ready.krivoshein.site/ "
                "и https://krivoshein.site/prays-list/"
            ),
            "site-fix": (
                "Диагностика сайта — от 5 000 ₽, ремонт/доработка — от 10 000 ₽. "
                "Прайс: https://krivoshein.site/prays-list/ · опишите, что сломалось."
            ),
        }
        if key and key in texts:
            return texts[key]
        # price question without clear service
        return (
            "Ориентиры «от» по всем услугам (WordPress, VPS, боты, Директ, лендинги, "
            "AI-ready) — https://krivoshein.site/prays-list/. "
            f"Можно уточнить направление (сейчас контекст: «{label}») — отвечу конкретнее."
        )

    def _fallback_service_reply_en(
        self, key: str | None, label: str, *, price_focus: bool
    ) -> str | None:
        texts = {
            "direct": (
                "Yandex Direct: consult from 2,000 ₽/h, audit from 10,000 ₽, "
                "setup from 20,000 ₽, management from 25,000 ₽/mo. "
                "https://direct.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "landing": (
                "Landings: simple from 25,000 ₽, with SEO blocks from 45,000 ₽, "
                "WordPress from 50,000 ₽. "
                "https://landing.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "wordpress": (
                "WordPress: fixes from 5,000 ₽, maintenance from 20,000 ₽/mo, "
                "corporate sites from 90,000 ₽. "
                "https://wordpress.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "vps": (
                "VPS turnkey setup from 10,000 ₽ (Linux, Nginx, Docker, SSL, backups). "
                "https://vps.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "bots": (
                "MAX/Telegram bots: simple lead bot from 40,000 ₽, "
                "CRM/integrations from 70,000 ₽. "
                "https://bots.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "ai-ready": (
                "AI-ready: Start from 10,000 ₽, Pro from 20,000 ₽, Bot-ready from 30,000 ₽. "
                "https://ai-ready.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "seo": (
                "Technical SEO / AI-search prep — see AI-ready packages: "
                "https://ai-ready.krivoshein.site/ · https://krivoshein.site/prays-list/"
            ),
            "site-fix": (
                "Site diagnostics from 5,000 ₽, fixes from 10,000 ₽. "
                "https://krivoshein.site/prays-list/"
            ),
        }
        if key and key in texts:
            return texts[key]
        if price_focus:
            return (
                f"“From” pricing for «{label}» and all services: "
                "https://krivoshein.site/prays-list/. Or Telegram @DrSlon."
            )
        return None

    async def create_lead(
        self,
        *,
        session_id: str,
        host: str,
        path: str,
        topic: str,
        need: str,
        budget: str,
        urgency: str,
        contact: str,
        client_ip: str,
        user_agent: str,
        honeypot: str = "",
        origin: str | None = None,
    ) -> dict:
        if honeypot.strip():
            # Fake success — do not create lead or notify admin
            logger.info(
                "Web rate/honeypot endpoint=lead reason=honeypot ip=%s origin=%s host=%s",
                client_ip,
                origin or "",
                host,
            )
            return {
                "ok": True,
                "lead_id": None,
                "message": "Спасибо! Мы скоро свяжемся.",
                "handoff": handoff_payload(),
            }

        host_n = normalize_host(host)
        path_n = path or "/"
        rate_key = f"ip:{client_ip}"
        own = is_own_ecosystem_origin(origin, host_n)
        # Hourly lead cap for everyone; external can be stricter via min().
        lead_limit = self._settings.web_lead_limit_per_hour
        ext_lead = self._settings.web_lead_limit_external_per_hour
        if not own and ext_lead > 0:
            lead_limit = min(lead_limit, ext_lead)
        day_cap = self._settings.web_lead_limit_per_day_ip

        if await self._store.is_rate_limited(
            rate_key, kind="lead", limit=lead_limit, window_hours=1.0
        ):
            logger.warning(
                "Web rate/limit endpoint=lead reason=hourly_limit ip=%s origin=%s "
                "host=%s limit=%s",
                client_ip,
                origin or "",
                host_n,
                lead_limit,
            )
            lead_limit_msg = (
                "Вы уже отправили несколько заявок. Если нужно что-то ещё — "
                "напишите напрямую в Telegram @DrSlon или на почту."
            )
            return {
                "ok": False,
                "lead_id": None,
                "message": lead_limit_msg,
                "handoff": handoff_payload(),
            }

        if day_cap > 0:
            day_count = await self._store.count_leads_for_ip(client_ip, hours=24.0)
            if day_count >= day_cap:
                logger.warning(
                    "Web rate/limit endpoint=lead reason=daily_ip_limit ip=%s origin=%s "
                    "host=%s count=%s cap=%s",
                    client_ip,
                    origin or "",
                    host_n,
                    day_count,
                    day_cap,
                )
                return {
                    "ok": False,
                    "lead_id": None,
                    "message": (
                        "Вы уже отправили несколько заявок. Если нужно что-то ещё — "
                        "напишите напрямую в Telegram @DrSlon или на почту."
                    ),
                    "handoff": handoff_payload(),
                }

        profile = profile_for_host(host_n)
        topic_final = (topic or "").strip() or str(profile.get("label") or "Веб-чат")
        urgency_final = (urgency or "Обычная").strip() or "Обычная"

        lead_id = await self._store.save_lead(
            session_id=session_id,
            host=host_n,
            path=path_n,
            topic=topic_final,
            need=need,
            budget=budget or "",
            urgency=urgency_final,
            contact=contact,
            client_ip=client_ip,
            user_agent=user_agent,
            extra={"source": "web_assistant"},
        )
        await self._store.record_rate(rate_key, kind="lead")
        await self._store.touch_session(session_id, host=host_n, path=path_n)

        notified = await self._notify_admin(
            lead_id=lead_id,
            session_id=session_id,
            host=host_n,
            path=path_n,
            topic=topic_final,
            need=need,
            budget=budget or "—",
            urgency=urgency_final,
            contact=contact,
            client_ip=client_ip,
        )

        msg = (
            "Заявка отправлена. Алексей свяжется с вами по указанному контакту."
            if notified
            else (
                "Заявка сохранена. Если ответа долго нет — напишите в Telegram @DrSlon "
                "или на https://krivoshein.site/contacts/"
            )
        )
        logger.info(
            "Web lead id=%s host=%s notified=%s session=%s",
            lead_id,
            host_n,
            notified,
            session_id[:8],
        )
        return {
            "ok": True,
            "lead_id": lead_id,
            "message": msg,
            "handoff": handoff_payload(),
        }

    async def _notify_admin(
        self,
        *,
        lead_id: int,
        session_id: str,
        host: str,
        path: str,
        topic: str,
        need: str,
        budget: str,
        urgency: str,
        contact: str,
        client_ip: str,
    ) -> bool:
        channel = self._settings.admin_channel_id
        if not channel or self._max is None:
            logger.warning("Web lead: no admin channel or max client")
            return False

        created = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
        text = "\n".join(
            [
                "🌐 Новая заявка (веб-чат)",
                "━━━━━━━━━━━━━━━━",
                f"🆔 Lead #{lead_id}",
                f"📌 Тема: {topic}",
                f"⚡ Срочность: {urgency}",
                f"🌍 Сайт: https://{host}{path}",
                f"📝 Задача:",
                need,
                f"💰 Бюджет: {budget}",
                f"📞 Контакт: {contact}",
                f"🔐 Session: {session_id[:12]}…",
                f"🛰 IP: {client_ip}",
                f"🕐 {created}",
            ]
        )
        try:
            await self._max.send_channel_message(channel, text)
            return True
        except MaxApiError:
            logger.exception("Web lead: MAX notify failed lead_id=%s", lead_id)
            return False
