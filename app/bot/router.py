from __future__ import annotations

import logging
import re
from typing import Any

from app.bot.faq import FAQ_ANSWERS, FAQ_PAYLOADS
from app.bot.keyboards import (
    MENU_DOCS,
    MENU_FAQ,
    MENU_LABELS,
    MENU_MAIN,
    MENU_OTHER,
    MENU_TICKET,
    TICKET_CONFIRM_CANCEL,
    TICKET_CONFIRM_SEND,
    TICKET_TOPIC_LABELS,
    TICKET_URGENCY_LABELS,
    get_faq_back_keyboard,
    get_faq_keyboard,
    get_main_menu,
    get_ticket_confirm_keyboard,
    get_ticket_nav_keyboard,
    get_ticket_topic_keyboard,
    get_ticket_urgency_keyboard,
)
from app.bot.states import TicketState
from app.bot.texts import (
    TICKET_CANCELLED_TEXT,
    TICKET_CONTACT_INVALID_TEXT,
    TICKET_CONTACT_TEXT,
    TICKET_DESCRIPTION_TEXT,
    TICKET_INVALID_INPUT_TEXT,
    TICKET_SUBMITTED_SUCCESS_TEXT,
    TICKET_TOPIC_TEXT,
    TICKET_URGENCY_TEXT,
    WELCOME_TEXT,
)
from app.config import settings
from app.max_api.client import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.max_api.types import ReplyMarkup
from app.tickets.models import TicketDraft, TicketSession
from app.tickets.service import format_admin_message, format_summary
from app.tickets.storage import TicketStorage

MAIN_MENU_TEXT = WELCOME_TEXT
FAQ_MENU_TEXT = "Выберите вопрос:"
RECEIVED_TEXT = "Получил сообщение"
START_COMMAND = "/start"

TICKET_ADMIN_NOT_CONFIGURED_TEXT = (
    "Сейчас не удалось отправить заявку: админ-канал не настроен. Попробуйте позже."
)
TICKET_ADMIN_SEND_FAILED_TEXT = (
    "Не удалось отправить заявку. Попробуйте позже или напишите напрямую."
)

TICKET_CALLBACK_PAYLOADS = {
    *TICKET_TOPIC_LABELS,
    *TICKET_URGENCY_LABELS,
    TICKET_CONFIRM_SEND,
    TICKET_CONFIRM_CANCEL,
}

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


def extract_chat_id(update: dict[str, Any]) -> int | None:
    chat_id = update.get("chat_id")
    if isinstance(chat_id, int):
        return chat_id

    message = update.get("message")
    if isinstance(message, dict):
        recipient = message.get("recipient")
        if isinstance(recipient, dict):
            recipient_chat_id = recipient.get("chat_id")
            if isinstance(recipient_chat_id, int):
                return recipient_chat_id

    callback = update.get("callback")
    if isinstance(callback, dict):
        callback_message = callback.get("message")
        if isinstance(callback_message, dict):
            recipient = callback_message.get("recipient")
            if isinstance(recipient, dict):
                recipient_chat_id = recipient.get("chat_id")
                if isinstance(recipient_chat_id, int):
                    return recipient_chat_id

    return None


def extract_message_text(update: dict[str, Any]) -> str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    body = message.get("body")
    if not isinstance(body, dict):
        return None

    text = body.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    return None


def extract_callback_payload(update: dict[str, Any]) -> str | None:
    callback = update.get("callback")
    if not isinstance(callback, dict):
        return None

    payload = callback.get("payload")
    if isinstance(payload, str) and payload.strip():
        return payload.strip()

    return None


def is_valid_contact(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    if _EMAIL_RE.match(normalized):
        return True
    digits = re.sub(r"\D", "", normalized)
    return len(digits) >= 10 and _PHONE_RE.match(normalized) is not None


class BotRouter:
    def __init__(self, client: MaxApiClient, storage: TicketStorage) -> None:
        self.client = client
        self.storage = storage
        self.logger = logging.getLogger(__name__)

    async def handle_update(self, update: dict[str, Any]) -> None:
        update_type = update.get("update_type", "unknown")
        chat_id = extract_chat_id(update)
        self.logger.info("Получен апдейт: update_type=%s, chat_id=%s", update_type, chat_id)

        if update_type == "bot_started":
            await self._handle_bot_started(chat_id)
            return

        if update_type == "message_created":
            await self._handle_message_created(update, chat_id)
            return

        if update_type == "message_callback":
            await self._handle_message_callback(update, chat_id)
            return

        self.logger.debug("Апдейт %s пока не обрабатывается", update_type)

    async def _handle_bot_started(self, chat_id: int | None) -> None:
        if chat_id is None:
            self.logger.warning("bot_started без chat_id, меню не отправлено")
            return

        await self.storage.delete_session(chat_id)
        self.logger.info("Пользователь запустил бота: chat_id=%s", chat_id)
        await self._send_main_menu(chat_id)

    async def _handle_message_created(self, update: dict[str, Any], chat_id: int | None) -> None:
        if chat_id is None:
            self.logger.warning("message_created без chat_id, ответ не отправлен")
            return

        text = extract_message_text(update)
        if text and text.lower() == START_COMMAND:
            self.logger.info("Команда /start от chat_id=%s", chat_id)
            await self.storage.delete_session(chat_id)
            await self._send_main_menu(chat_id)
            return

        if await self.storage.has_active_ticket_flow(chat_id):
            await self._handle_ticket_text(chat_id, text)
            return

        if text:
            self.logger.info("Текстовое сообщение от chat_id=%s: %s", chat_id, text)
            reply = f"{RECEIVED_TEXT}\nВы написали: {text}"
        else:
            self.logger.info("Сообщение без текста от chat_id=%s", chat_id)
            reply = RECEIVED_TEXT

        await self._send_message(chat_id, reply)

    async def _handle_message_callback(self, update: dict[str, Any], chat_id: int | None) -> None:
        payload = extract_callback_payload(update)

        if chat_id is None:
            self.logger.warning("message_callback без chat_id, ответ не отправлен")
            return

        self.logger.info("Нажата кнопка: chat_id=%s, payload=%s", chat_id, payload)

        if payload == MENU_TICKET:
            await self._start_ticket_flow(chat_id)
            return

        if payload in TICKET_CALLBACK_PAYLOADS:
            await self._handle_ticket_callback(chat_id, payload)
            return

        if payload == MENU_FAQ:
            await self._show_faq_menu(chat_id)
            return

        if payload in FAQ_PAYLOADS:
            await self._handle_faq_answer(chat_id, payload)
            return

        if payload == MENU_MAIN:
            await self._send_main_menu(chat_id)
            return

        if await self.storage.has_active_ticket_flow(chat_id):
            await self._send_message(
                chat_id,
                TICKET_INVALID_INPUT_TEXT,
            )
            return

        if payload and payload in MENU_LABELS:
            section = MENU_LABELS[payload]
            if payload in {MENU_DOCS, MENU_OTHER}:
                reply = f'Раздел «{section}» скоро будет доступен.'
            else:
                reply = "Эта кнопка пока не настроена."
            await self._send_message(chat_id, reply)
            return

        await self._send_message(chat_id, "Эта кнопка пока не настроена.")

    async def _start_ticket_flow(self, chat_id: int) -> None:
        session = TicketSession(chat_id=chat_id, state=TicketState.TICKET_TOPIC, draft=TicketDraft())
        await self.storage.save_session(session)
        self.logger.info("Старт сценария заявки: chat_id=%s", chat_id)
        await self._send_message(chat_id, TICKET_TOPIC_TEXT, reply_markup=get_ticket_topic_keyboard())

    async def _handle_ticket_callback(self, chat_id: int, payload: str) -> None:
        session = await self.storage.get_session(chat_id)
        if session is None or session.state == TicketState.IDLE:
            await self._send_message(chat_id, "Сначала начните подачу заявки через главное меню.")
            return

        if payload in TICKET_TOPIC_LABELS:
            if session.state != TicketState.TICKET_TOPIC:
                await self._send_message(chat_id, TICKET_INVALID_INPUT_TEXT)
                return

            session.draft.topic = TICKET_TOPIC_LABELS[payload]
            session.state = TicketState.TICKET_DESCRIPTION
            await self.storage.save_session(session)
            await self._send_message(
                chat_id,
                TICKET_DESCRIPTION_TEXT,
                reply_markup=get_ticket_nav_keyboard(),
            )
            return

        if payload in TICKET_URGENCY_LABELS:
            if session.state != TicketState.TICKET_URGENCY:
                await self._send_message(chat_id, TICKET_INVALID_INPUT_TEXT)
                return

            session.draft.urgency = TICKET_URGENCY_LABELS[payload]
            session.state = TicketState.TICKET_CONFIRM
            await self.storage.save_session(session)
            await self._send_message(
                chat_id,
                format_summary(session.draft),
                reply_markup=get_ticket_confirm_keyboard(),
            )
            return

        if payload == TICKET_CONFIRM_SEND:
            if session.state != TicketState.TICKET_CONFIRM:
                await self._send_message(chat_id, "Сначала заполните все поля заявки.")
                return
            await self._submit_ticket(chat_id, session)
            return

        if payload == TICKET_CONFIRM_CANCEL:
            await self._cancel_ticket(chat_id)
            return

    async def _handle_ticket_text(self, chat_id: int, text: str | None) -> None:
        session = await self.storage.get_session(chat_id)
        if session is None:
            return

        if not text:
            await self._send_message(chat_id, "Пожалуйста, отправьте текстовое сообщение.")
            return

        if session.state == TicketState.TICKET_TOPIC:
            await self._send_message(
                chat_id,
                TICKET_INVALID_INPUT_TEXT,
                reply_markup=get_ticket_topic_keyboard(),
            )
            return

        if session.state == TicketState.TICKET_DESCRIPTION:
            session.draft.description = text
            session.state = TicketState.TICKET_CONTACT
            await self.storage.save_session(session)
            await self._send_message(
                chat_id,
                TICKET_CONTACT_TEXT,
                reply_markup=get_ticket_nav_keyboard(),
            )
            return

        if session.state == TicketState.TICKET_CONTACT:
            if not is_valid_contact(text):
                await self._send_message(
                    chat_id,
                    TICKET_CONTACT_INVALID_TEXT,
                    reply_markup=get_ticket_nav_keyboard(),
                )
                return

            session.draft.contact = text.strip()
            session.state = TicketState.TICKET_URGENCY
            await self.storage.save_session(session)
            await self._send_message(
                chat_id,
                TICKET_URGENCY_TEXT,
                reply_markup=get_ticket_urgency_keyboard(),
            )
            return

        if session.state == TicketState.TICKET_URGENCY:
            await self._send_message(
                chat_id,
                TICKET_INVALID_INPUT_TEXT,
                reply_markup=get_ticket_urgency_keyboard(),
            )
            return

        if session.state == TicketState.TICKET_CONFIRM:
            await self._send_message(
                chat_id,
                TICKET_INVALID_INPUT_TEXT,
                reply_markup=get_ticket_confirm_keyboard(),
            )
            return

    async def _submit_ticket(self, chat_id: int, session: TicketSession) -> None:
        admin_channel_id = settings.admin_channel_id
        if admin_channel_id is None:
            self.logger.error("ADMIN_CHANNEL_ID не настроен, заявка не отправлена")
            await self._send_message(chat_id, TICKET_ADMIN_NOT_CONFIGURED_TEXT)
            return

        admin_text = format_admin_message(session.draft, chat_id)
        try:
            await self.client.send_message(admin_channel_id, admin_text)
        except MaxApiError:
            self.logger.exception(
                "Не удалось отправить заявку в admin_channel_id=%s",
                admin_channel_id,
            )
            await self._send_message(chat_id, TICKET_ADMIN_SEND_FAILED_TEXT)
            return

        self.logger.info(
            "Заявка отправлена: chat_id=%s, topic=%s, urgency=%s",
            chat_id,
            session.draft.topic,
            session.draft.urgency,
        )
        await self.storage.delete_session(chat_id)
        await self._send_message(chat_id, TICKET_SUBMITTED_SUCCESS_TEXT)
        await self._send_main_menu(chat_id)

    async def _cancel_ticket(self, chat_id: int) -> None:
        await self.storage.delete_session(chat_id)
        await self._send_message(chat_id, TICKET_CANCELLED_TEXT)
        await self._send_main_menu(chat_id)

    async def _show_faq_menu(self, chat_id: int) -> None:
        await self._send_message(chat_id, FAQ_MENU_TEXT, reply_markup=get_faq_keyboard())

    async def _handle_faq_answer(self, chat_id: int, payload: str) -> None:
        question, answer = FAQ_ANSWERS[payload]
        self.logger.info("FAQ вопрос от chat_id=%s: %s", chat_id, question)
        await self._send_message(
            chat_id,
            f"{question}\n\n{answer}",
            reply_markup=get_faq_back_keyboard(),
        )

    async def _send_main_menu(self, chat_id: int) -> None:
        await self._send_message(chat_id, MAIN_MENU_TEXT, reply_markup=get_main_menu())

    async def _send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: ReplyMarkup | None = None,
    ) -> None:
        try:
            await self.client.send_message(chat_id, text, reply_markup=reply_markup)
        except MaxApiError:
            self.logger.exception("Не удалось отправить сообщение в chat_id=%s", chat_id)