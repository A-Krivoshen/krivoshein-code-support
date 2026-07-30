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
    ) -> dict:
        if honeypot.strip():
            # silent success for bots
            logger.info("Web chat honeypot trip ip=%s", client_ip)
            return {
                "session_id": session_id,
                "reply": "Спасибо! Если вопрос срочный — напишите в Telegram @DrSlon.",
                "suggest_lead": False,
                "quick_replies": [],
            }

        host_n = normalize_host(host)
        path_n = path or "/"
        rate_key = f"ip:{client_ip}"
        limit = self._settings.web_rate_limit_per_hour

        if await self._store.is_rate_limited(rate_key, kind="chat", limit_per_hour=limit):
            en = _looks_english(message)
            return {
                "session_id": session_id,
                "reply": (
                    "Too many messages this hour. "
                    "Please write on Telegram @DrSlon or https://krivoshein.site/contacts/"
                    if en
                    else (
                        "Слишком много сообщений за час. "
                        "Напишите в Telegram @DrSlon или на https://krivoshein.site/contacts/"
                    )
                ),
                "suggest_lead": True,
                "quick_replies": (
                    ["Leave a lead", "Telegram"] if en else ["Оставить заявку", "Telegram"]
                ),
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
            except LlmError as exc:
                logger.warning("Web LLM failed: %s", exc)
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
                except Exception:
                    logger.warning("Web LLM Russian retry failed", exc_info=True)
        else:
            reply_text = None

        if not reply_text:
            reply_text = self._fallback_reply(message, profile)

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
        low = message.lower()
        label = str(profile.get("label") or "услугам")
        en = _looks_english(message)
        if en:
            if any(w in low for w in ("price", "cost", "how much", "pricing")):
                return (
                    f"Pricing for «{label}» is on https://krivoshein.site/prays-list/ "
                    "and this page. Exact quote after a short brief. "
                    "You can leave a lead here or write Telegram @DrSlon."
                )
            if any(w in low for w in ("lead", "order", "contact", "hire")):
                return (
                    "Use the «Leave a lead» button in this chat (task + contact), "
                    "or Telegram @DrSlon / MAX, or https://krivoshein.site/contacts/"
                )
            if "telegram" in low or "@drslon" in low:
                return "Telegram: https://t.me/DrSlon"
            return (
                f"Briefly about «{label}»: describe the task — I'll suggest a format "
                "and “from” pricing. Ready to talk — leave a lead or write @DrSlon. "
                "Pricing: https://krivoshein.site/prays-list/"
            )
        if any(w in low for w in ("цена", "стоим", "прайс", "сколько")):
            return (
                f"Ориентиры по «{label}» — в прайсе: https://krivoshein.site/prays-list/ "
                "и в описании этой страницы. Точная смета после короткого брифа. "
                "Можете оставить заявку здесь или написать в Telegram @DrSlon."
            )
        if any(w in low for w in ("заявк", "заказ", "свяж", "контакт")):
            return (
                "Оставьте заявку кнопкой «Оставить заявку» в этом чате "
                "(задача + контакт), либо напишите в Telegram @DrSlon / MAX, "
                "либо форма: https://krivoshein.site/contacts/"
            )
        if "telegram" in low or "тг" in low or "@drslon" in low:
            return "Telegram: https://t.me/DrSlon"
        return (
            f"Кратко по «{label}»: опишите задачу — подскажу формат и ориентир «от». "
            "Готовы обсудить — оставьте заявку или напишите @DrSlon. "
            "Прайс: https://krivoshein.site/prays-list/"
        )

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
    ) -> dict:
        if honeypot.strip():
            logger.info("Web lead honeypot trip ip=%s", client_ip)
            return {
                "ok": True,
                "lead_id": None,
                "message": "Спасибо! Мы скоро свяжемся.",
                "handoff": handoff_payload(),
            }

        host_n = normalize_host(host)
        path_n = path or "/"
        rate_key = f"ip:{client_ip}"
        lead_limit = max(3, self._settings.web_rate_limit_per_hour // 4)

        if await self._store.is_rate_limited(
            rate_key, kind="lead", limit_per_hour=lead_limit
        ):
            return {
                "ok": False,
                "lead_id": None,
                "message": (
                    "Слишком много заявок с вашего IP. "
                    "Напишите напрямую: https://t.me/DrSlon"
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
