from __future__ import annotations

import logging
from typing import Any

from app.bot.faq import FAQ_ANSWERS, FAQ_PAYLOADS
from app.bot.parsing import (
    extract_callback_payload,
    extract_chat_id,
    extract_message_text,
    is_valid_contact,
)
from app.bot.keyboards import (
    MENU_DOCS,
    MENU_FAQ,
    MENU_FAQ_BACK,
    MENU_LABELS,
    MENU_MAIN,
    MENU_OTHER,
    MENU_TICKET,
    OTHER_TASK,
    TICKET_CONFIRM_CANCEL,
    TICKET_CONFIRM_SEND,
    TICKET_DESCRIPTION_NEXT,
    TICKET_TOPIC_LABELS,
    TICKET_TOPIC_OTHER,
    TICKET_URGENCY_LABELS,
    get_faq_back_keyboard,
    get_faq_keyboard,
    get_main_menu,
    get_other_menu_keyboard,
    get_ticket_confirm_keyboard,
    get_ticket_description_keyboard,
    get_ticket_nav_keyboard,
    get_ticket_topic_keyboard,
    get_ticket_urgency_keyboard,
)
from app.bot.states import TicketState
from app.bot.texts import (
    BTN_TO_MENU,
    TICKET_CANCELLED_TEXT,
    TICKET_CONTACT_INVALID_TEXT,
    TICKET_CONTACT_TEXT,
    TICKET_DESCRIPTION_EMPTY_TEXT,
    TICKET_DESCRIPTION_PROMPT_TEXT,
    TICKET_DESCRIPTION_SAVED_TEXT,
    TICKET_DESCRIPTION_TEXT,
    TICKET_INVALID_INPUT_TEXT,
    TICKET_MEDIA_NOT_HERE_TEXT,
    TICKET_MEDIA_REJECTED_TEXT,
    TICKET_MEDIA_SAVED_TEXT,
    TICKET_SUBMITTED_MEDIA_PARTIAL_TEXT,
    TICKET_SUBMITTED_SUCCESS_TEXT,
    OTHER_MENU_TEXT,
    OTHER_TASK_TEXT,
    TICKET_TOPIC_TEXT,
    TICKET_URGENCY_TEXT,
    WELCOME_TEXT,
)
from app.config import settings
from app.max_api.client import MaxApiClient
from app.max_api.exceptions import MaxApiError
from app.max_api.types import ReplyMarkup
from app.tickets.media import append_ticket_media, extract_ticket_media
from app.tickets.models import TicketDraft, TicketSession
from app.tickets.service import format_summary, send_ticket_to_admin
from app.tickets.storage import TicketStorage

_logger = logging.getLogger(__name__)

MAIN_MENU_TEXT = WELCOME_TEXT
FAQ_MENU_TEXT = (
    "Частые вопросы по услугам: сайты, поддержка, реклама, боты и серверы.\n\n"
    "Выберите интересующий раздел — отвечу кратко, с ориентирами по срокам."
)
START_COMMAND = "/start"
_MENU_COMMANDS = {START_COMMAND, "start", "старт", "меню", BTN_TO_MENU.lower()}

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
    TICKET_DESCRIPTION_NEXT,
}

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

        await self._reset_to_main_menu(chat_id, reason="bot_started")

    async def _handle_message_created(self, update: dict[str, Any], chat_id: int | None) -> None:
        if chat_id is None:
            self.logger.warning("message_created без chat_id, ответ не отправлен")
            return

        text = extract_message_text(update)
        if _is_reset_command(text):
            self.logger.info("Команда сброса от chat_id=%s: %s", chat_id, text.strip())
            await self._reset_to_main_menu(chat_id, reason="reset_command")
            return

        if await self.storage.has_active_ticket_flow(chat_id):
            await self._handle_ticket_message(chat_id, update)
            return

        await self._handle_idle_message(chat_id, text)

    async def _handle_idle_message(self, chat_id: int, text: str | None) -> None:
        if text:
            stripped = text.strip()

            for payload, label in MENU_LABELS.items():
                if stripped == label:
                    self.logger.info(
                        "Текстовый выбор меню от chat_id=%s: payload=%s",
                        chat_id,
                        payload,
                    )
                    await self._handle_menu_payload(chat_id, payload)
                    return

            self.logger.info("Неизвестное сообщение от chat_id=%s: %s", chat_id, stripped)

        await self._send_main_menu(chat_id)

    async def _handle_menu_payload(self, chat_id: int, payload: str) -> None:
        if payload == MENU_TICKET:
            await self._start_ticket_flow(chat_id)
            return

        if payload == MENU_FAQ:
            await self._show_faq_menu(chat_id)
            return

        if payload == MENU_OTHER:
            await self._show_other_menu(chat_id)
            return

        if payload == MENU_DOCS:
            await self._send_message(chat_id, 'Раздел «Документация» скоро будет доступен.')
            return

        if payload == MENU_MAIN:
            await self._reset_to_main_menu(chat_id, reason="menu_main")
            return

        await self._send_message(chat_id, "Эта кнопка пока не настроена.")

    async def _handle_message_callback(self, update: dict[str, Any], chat_id: int | None) -> None:
        payload = extract_callback_payload(update)

        if chat_id is None:
            self.logger.warning("message_callback без chat_id, ответ не отправлен")
            return

        self.logger.info("Нажата кнопка: chat_id=%s, payload=%s", chat_id, payload)

        if payload == TICKET_CONFIRM_CANCEL:
            await self._reset_to_main_menu(
                chat_id,
                reason="cancel_button",
                show_cancelled_message=True,
            )
            return

        if payload == MENU_MAIN:
            await self._reset_to_main_menu(chat_id, reason="menu_main")
            return

        if payload in TICKET_CALLBACK_PAYLOADS:
            await self._handle_ticket_callback(chat_id, payload)
            return

        if payload == OTHER_TASK:
            await self._start_other_task_flow(chat_id)
            return

        if payload == MENU_FAQ_BACK:
            await self._show_faq_menu(chat_id)
            return

        if payload in FAQ_PAYLOADS:
            await self._handle_faq_answer(chat_id, payload)
            return

        if await self.storage.has_active_ticket_flow(chat_id):
            await self._send_message(
                chat_id,
                TICKET_INVALID_INPUT_TEXT,
            )
            return

        if payload and payload in MENU_LABELS:
            await self._handle_menu_payload(chat_id, payload)
            return

        await self._send_message(chat_id, "Эта кнопка пока не настроена.")

    async def _start_ticket_flow(self, chat_id: int) -> None:
        session = TicketSession(chat_id=chat_id, state=TicketState.TICKET_TOPIC, draft=TicketDraft())
        await self.storage.save_session(session)
        self.logger.info("Старт сценария заявки: chat_id=%s", chat_id)
        await self._send_message(chat_id, TICKET_TOPIC_TEXT, reply_markup=get_ticket_topic_keyboard())

    async def _start_other_task_flow(self, chat_id: int) -> None:
        session = TicketSession(
            chat_id=chat_id,
            state=TicketState.TICKET_DESCRIPTION,
            draft=TicketDraft(topic=TICKET_TOPIC_LABELS[TICKET_TOPIC_OTHER]),
        )
        await self.storage.save_session(session)
        self.logger.info("Старт заявки «Другая задача»: chat_id=%s", chat_id)
        await self._send_message(
            chat_id,
            OTHER_TASK_TEXT,
            reply_markup=get_ticket_description_keyboard(),
        )

    async def _show_other_menu(self, chat_id: int) -> None:
        await self._send_message(chat_id, OTHER_MENU_TEXT, reply_markup=get_other_menu_keyboard())

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
                reply_markup=get_ticket_description_keyboard(),
            )
            return

        if payload == TICKET_DESCRIPTION_NEXT:
            if session.state != TicketState.TICKET_DESCRIPTION:
                await self._send_message(chat_id, TICKET_INVALID_INPUT_TEXT)
                return

            if not session.draft.description.strip():
                await self._send_message(
                    chat_id,
                    TICKET_DESCRIPTION_EMPTY_TEXT,
                    reply_markup=get_ticket_description_keyboard(),
                )
                return

            session.state = TicketState.TICKET_CONTACT
            await self.storage.save_session(session)
            await self._send_message(
                chat_id,
                TICKET_CONTACT_TEXT,
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

    async def _handle_ticket_message(self, chat_id: int, update: dict[str, Any]) -> None:
        session = await self.storage.get_session(chat_id)
        if session is None:
            return

        text = extract_message_text(update)
        media_items = extract_ticket_media(update)

        if session.state == TicketState.TICKET_DESCRIPTION:
            handled = False

            if media_items:
                added = 0
                rejected = 0
                for media_item in media_items:
                    if append_ticket_media(session.draft, media_item):
                        added += 1
                    elif media_item.is_valid():
                        rejected += 1

                if added:
                    await self.storage.save_session(session)
                    await self._send_message(
                        chat_id,
                        TICKET_MEDIA_SAVED_TEXT.format(
                            count=len(session.draft.forwardable_media()),
                        ),
                        reply_markup=get_ticket_description_keyboard(),
                    )
                    handled = True

                if rejected:
                    await self._send_message(
                        chat_id,
                        TICKET_MEDIA_REJECTED_TEXT,
                        reply_markup=get_ticket_description_keyboard(),
                    )
                    handled = True

            if text:
                session.draft.description = text
                await self.storage.save_session(session)
                if not media_items:
                    await self._send_message(
                        chat_id,
                        TICKET_DESCRIPTION_SAVED_TEXT,
                        reply_markup=get_ticket_description_keyboard(),
                    )
                handled = True

            if not handled:
                await self._send_message(
                    chat_id,
                    TICKET_DESCRIPTION_PROMPT_TEXT,
                    reply_markup=get_ticket_description_keyboard(),
                )
            return

        if not text:
            if media_items:
                await self._send_message(chat_id, TICKET_MEDIA_NOT_HERE_TEXT)
            else:
                await self._send_message(chat_id, "Пожалуйста, отправьте текстовое сообщение.")
            return

        if session.state == TicketState.TICKET_TOPIC:
            await self._send_message(
                chat_id,
                TICKET_INVALID_INPUT_TEXT,
                reply_markup=get_ticket_topic_keyboard(),
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

        result = await send_ticket_to_admin(
            self.client,
            admin_channel_id,
            session.draft,
            chat_id,
        )
        if not result.text_sent:
            await self._send_message(chat_id, TICKET_ADMIN_SEND_FAILED_TEXT)
            return

        self.logger.info(
            "Заявка отправлена: chat_id=%s, topic=%s, urgency=%s, media_sent=%s, media_failed=%s",
            chat_id,
            session.draft.topic,
            session.draft.urgency,
            result.media_sent,
            result.media_failed,
        )
        await self.storage.delete_session(chat_id)
        if result.media_total > 0 and result.media_failed > 0:
            await self._send_message(chat_id, TICKET_SUBMITTED_MEDIA_PARTIAL_TEXT)
        else:
            await self._send_message(chat_id, TICKET_SUBMITTED_SUCCESS_TEXT)
        await self._send_main_menu(chat_id)

    async def _reset_to_main_menu(
        self,
        chat_id: int,
        *,
        reason: str,
        show_cancelled_message: bool = False,
    ) -> None:
        await self.storage.delete_session(chat_id)
        self.logger.info("Сброс сессии: chat_id=%s, reason=%s", chat_id, reason)
        if show_cancelled_message:
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