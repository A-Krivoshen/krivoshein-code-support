from __future__ import annotations

import re

from app.bot.keyboards import (
    TICKET_TOPIC_BOTS,
    TICKET_TOPIC_DIRECT,
    TICKET_TOPIC_LANDING,
    TICKET_TOPIC_LABELS,
    TICKET_TOPIC_VPS,
    TICKET_TOPIC_WORDPRESS,
)

# (payload, keywords) — порядок: более специфичные раньше
_TOPIC_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        TICKET_TOPIC_WORDPRESS,
        (
            "wordpress",
            "вордпресс",
            "wp ",
            " wp",
            "плагин",
            "plugin",
            "acf",
            "woocommerce",
            "вукоммерс",
            "тема wordpress",
            "сайт тормозит",
            "сайт упал",
            "белый экран",
            "elementor",
            "gutenberg",
        ),
    ),
    (
        TICKET_TOPIC_VPS,
        (
            "vps",
            "сервер",
            "server",
            "nginx",
            "docker",
            "ubuntu",
            "debian",
            "ssl",
            "certbot",
            "хостинг",
            "hosting",
            "linux",
            "ssh",
            "firewall",
            "zram",
            "прокси",
            "proxy",
        ),
    ),
    (
        TICKET_TOPIC_BOTS,
        (
            "бот",
            "bot",
            "telegram",
            "телеграм",
            "мессенджер max",
            "боты для max",
            "webhook",
            "aiogram",
        ),
    ),
    (
        TICKET_TOPIC_DIRECT,
        (
            "директ",
            "direct",
            "яндекс.директ",
            "yandex direct",
            "реклам",
            "кампани",
            "контекстн",
            "объявлен",
            "метрик",
        ),
    ),
    (
        TICKET_TOPIC_LANDING,
        (
            "лендинг",
            "landing",
            "сайт под ключ",
            "новый сайт",
            "сделать сайт",
            "разработк сайта",
            "одностранич",
        ),
    ),
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def infer_topic_payload(*texts: str) -> str | None:
    """Эвристика темы по ключевым словам.

    Возвращает payload только при явной доминанте одной темы.
    Если ничья / нет сигналов — None (пользователь выберет сам).
    """
    blob = _normalize(" ".join(t for t in texts if t))
    if not blob:
        return None

    scores: dict[str, int] = {}
    for payload, keywords in _TOPIC_KEYWORDS:
        score = 0
        for kw in keywords:
            if kw in blob:
                score += 1
        if score:
            scores[payload] = score

    if not scores:
        return None

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_payload, best_score = ranked[0]
    if best_score < 1:
        return None
    if len(ranked) > 1 and ranked[1][1] == best_score:
        # Ничья — не угадываем
        return None
    return best_payload


def infer_topic_label(*texts: str) -> str | None:
    payload = infer_topic_payload(*texts)
    if payload is None:
        return None
    return TICKET_TOPIC_LABELS.get(payload)


def build_description_from_user_texts(user_texts: list[str], *, max_chars: int = 1500) -> str:
    """Склеивает недавние user-сообщения (от старых к новым) в описание черновика."""
    if not user_texts:
        return ""
    # user_texts приходит newest-first
    ordered = list(reversed([t.strip() for t in user_texts if t and t.strip()]))
    # убираем дубли подряд
    deduped: list[str] = []
    for text in ordered:
        if deduped and deduped[-1] == text:
            continue
        deduped.append(text)
    joined = "\n\n".join(deduped)
    if len(joined) > max_chars:
        return joined[: max_chars - 1].rstrip() + "…"
    return joined
