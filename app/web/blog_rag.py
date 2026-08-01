"""Blog RAG demo: index WordPress posts → retrieve → answer via GigaChat (Groq fallback).

Shows how a knowledge base over the site blog can work for clients (AI-ready package).
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, settings
from app.llm.client import LlmClient, LlmError
from app.llm.gigachat import GigaChatClient

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}")


@dataclass
class BlogChunk:
    post_id: int
    title: str
    url: str
    date: str
    text: str
    # lowercased for matching
    haystack: str


def _strip_html(raw: str) -> str:
    text = html.unescape(raw or "")
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]


class BlogRagService:
    """In-memory blog index with disk cache + RAG answers."""

    def __init__(
        self,
        config: Settings | None = None,
        *,
        index_path: Path | None = None,
        blog_api: str = "https://krivoshein.site/wp-json/wp/v2",
    ) -> None:
        self._settings = config or settings
        self._blog_api = blog_api.rstrip("/")
        self._index_path = index_path or Path("data/blog_rag_index.json")
        self._chunks: list[BlogChunk] = []
        self._built_at: float = 0.0
        self._post_count: int = 0
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(timeout=30.0)
        self._giga: GigaChatClient | None = None
        self._llm: LlmClient | None = None

    @property
    def ready(self) -> bool:
        return bool(self._chunks)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "posts": self._post_count,
            "chunks": len(self._chunks),
            "built_at": self._built_at,
            "built_age_sec": int(time.time() - self._built_at) if self._built_at else None,
            "provider_preferred": (
                "gigachat" if self._settings.gigachat_enabled else "groq"
            ),
            "blog_api": self._blog_api,
        }

    async def aclose(self) -> None:
        await self._http.aclose()
        if self._giga is not None:
            await self._giga.aclose()
        if self._llm is not None:
            await self._llm.aclose()

    def _get_giga(self) -> GigaChatClient | None:
        if not self._settings.gigachat_enabled:
            return None
        if self._giga is None:
            self._giga = GigaChatClient(self._settings)
        return self._giga if self._giga.is_configured else None

    def _get_llm(self) -> LlmClient:
        if self._llm is None:
            # Failover client (Groq → GigaChat) for backup path
            self._llm = LlmClient(self._settings)
        return self._llm

    async def ensure_index(self, *, max_age_sec: float = 6 * 3600) -> None:
        """Load from disk or rebuild if stale/empty."""
        async with self._lock:
            now = time.time()
            if self._chunks and self._built_at and (now - self._built_at) < max_age_sec:
                return
            if not self._chunks:
                self._load_disk()
            if self._chunks and self._built_at and (now - self._built_at) < max_age_sec:
                return
            # Stale or empty → rebuild from WP REST
            await self._rebuild_unlocked()

    async def reindex(self) -> dict[str, Any]:
        async with self._lock:
            await self._rebuild_unlocked()
        return self.stats

    def _load_disk(self) -> bool:
        path = self._index_path
        if not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            chunks_raw = data.get("chunks") or []
            self._chunks = [
                BlogChunk(
                    post_id=int(c["post_id"]),
                    title=str(c["title"]),
                    url=str(c["url"]),
                    date=str(c.get("date") or ""),
                    text=str(c["text"]),
                    haystack=str(c.get("haystack") or c["text"]).lower(),
                )
                for c in chunks_raw
                if c.get("text")
            ]
            self._post_count = int(data.get("posts") or 0)
            self._built_at = float(data.get("built_at") or 0)
            logger.info(
                "Blog RAG index loaded from disk posts=%s chunks=%s",
                self._post_count,
                len(self._chunks),
            )
            return bool(self._chunks)
        except Exception:
            logger.exception("Blog RAG disk load failed")
            return False

    def _save_disk(self) -> None:
        path = self._index_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "built_at": self._built_at,
            "posts": self._post_count,
            "chunks": [asdict(c) for c in self._chunks],
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    async def _rebuild_unlocked(self) -> None:
        logger.info("Blog RAG reindex start api=%s", self._blog_api)
        chunks: list[BlogChunk] = []
        post_ids: set[int] = set()
        page = 1
        per_page = 50
        # Cap for demo reliability (full blog is fine ~393)
        max_pages = 12

        while page <= max_pages:
            url = f"{self._blog_api}/posts"
            try:
                r = await self._http.get(
                    url,
                    params={
                        "per_page": per_page,
                        "page": page,
                        "status": "publish",
                        "_fields": "id,title,link,date,content",
                    },
                )
            except httpx.HTTPError as exc:
                logger.warning("Blog RAG fetch error page=%s: %s", page, type(exc).__name__)
                break

            if r.status_code == 400:
                break
            if r.status_code >= 400:
                logger.warning("Blog RAG HTTP %s page=%s", r.status_code, page)
                break

            items = r.json()
            if not isinstance(items, list) or not items:
                break

            for item in items:
                try:
                    pid = int(item["id"])
                    title = _strip_html(
                        item.get("title", {}).get("rendered")
                        if isinstance(item.get("title"), dict)
                        else str(item.get("title") or "")
                    )
                    link = str(item.get("link") or "")
                    date = str(item.get("date") or "")[:10]
                    body = _strip_html(
                        item.get("content", {}).get("rendered")
                        if isinstance(item.get("content"), dict)
                        else str(item.get("content") or "")
                    )
                except Exception:
                    continue

                if not body or not link:
                    continue
                post_ids.add(pid)
                # Chunk long posts
                for piece in self._chunk_text(body, max_chars=1200):
                    hay = f"{title}\n{piece}".lower()
                    chunks.append(
                        BlogChunk(
                            post_id=pid,
                            title=title,
                            url=link,
                            date=date,
                            text=piece,
                            haystack=hay,
                        )
                    )

            total_pages = int(r.headers.get("X-WP-TotalPages") or "1")
            if page >= total_pages:
                break
            page += 1

        # Knowledge pages (price list etc.) + site llms.txt — not only blog posts.
        await self._append_knowledge_pages(chunks, post_ids)
        await self._append_llms_txt(chunks, post_ids)

        self._chunks = chunks
        self._post_count = len(post_ids)
        self._built_at = time.time()
        self._save_disk()
        logger.info(
            "Blog RAG reindex done posts=%s chunks=%s",
            self._post_count,
            len(self._chunks),
        )

    async def _append_knowledge_pages(
        self, chunks: list[BlogChunk], post_ids: set[int]
    ) -> None:
        """Index key pages: прайс, contacts — via REST + rendered HTML fallback."""
        slugs = ("prays-list", "contacts", "oferta")
        for slug in slugs:
            try:
                r = await self._http.get(
                    f"{self._blog_api}/pages",
                    params={
                        "slug": slug,
                        "status": "publish",
                        "_fields": "id,title,link,date,content",
                    },
                )
            except httpx.HTTPError as exc:
                logger.warning("Blog RAG page fetch %s: %s", slug, type(exc).__name__)
                continue
            if r.status_code >= 400:
                continue
            items = r.json()
            if not isinstance(items, list) or not items:
                continue
            item = items[0]
            try:
                pid = int(item["id"])
                title = _strip_html(
                    item.get("title", {}).get("rendered")
                    if isinstance(item.get("title"), dict)
                    else str(item.get("title") or "")
                )
                link = str(item.get("link") or f"https://krivoshein.site/{slug}/")
                date = str(item.get("date") or "")[:10]
                body = _strip_html(
                    item.get("content", {}).get("rendered")
                    if isinstance(item.get("content"), dict)
                    else str(item.get("content") or "")
                )
            except Exception:
                continue

            # Shortcode-only pages (price list) need rendered HTML.
            if len(body) < 200 or "[" in body:
                body = await self._fetch_rendered_text(link) or body

            if not body or len(body) < 80:
                continue

            post_ids.add(pid)
            # Boost price keywords in haystack for retrieval.
            boost = ""
            if slug == "prays-list":
                boost = (
                    "\nпрайс цены стоимость тарифы сколько стоит "
                    "руб ₽ прайс-лист price list"
                )
                title = title or "Прайс-лист (цены на услуги)"

            for piece in self._chunk_text(body, max_chars=1400):
                hay = f"{title}\n{piece}{boost}".lower()
                chunks.append(
                    BlogChunk(
                        post_id=pid,
                        title=title,
                        url=link,
                        date=date,
                        text=piece,
                        haystack=hay,
                    )
                )

    async def _append_llms_txt(
        self, chunks: list[BlogChunk], post_ids: set[int]
    ) -> None:
        """Index public llms.txt (already has structured prices)."""
        urls = (
            "https://krivoshein.site/llms.txt",
            "https://ai-ready.krivoshein.site/llms.txt",
        )
        for i, url in enumerate(urls):
            try:
                r = await self._http.get(url)
            except httpx.HTTPError:
                continue
            if r.status_code >= 400 or not r.text:
                continue
            text = r.text.strip()
            if len(text) < 100:
                continue
            pid = -10 - i  # synthetic ids
            post_ids.add(pid)
            title = (
                "Прайс и факты сайта (llms.txt)"
                if "krivoshein.site/llms" in url
                else "AI-ready: цены и пакеты (llms.txt)"
            )
            boost = (
                "\nпрайс цены стоимость тарифы сколько стоит "
                "руб ₽ rate hour диагностика vps директ бот ai-ready"
            )
            for piece in self._chunk_text(text, max_chars=1400):
                chunks.append(
                    BlogChunk(
                        post_id=pid,
                        title=title,
                        url=url if url.endswith(".txt") else url,
                        date="",
                        text=piece,
                        haystack=f"{title}\n{piece}{boost}".lower(),
                    )
                )

    async def _fetch_rendered_text(self, page_url: str) -> str:
        """GET public HTML page and strip to text (for shortcode pages)."""
        try:
            r = await self._http.get(
                page_url,
                headers={"User-Agent": "KRV-BlogRAG/1.0 (+https://krivoshein.site)"},
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            logger.warning("Blog RAG render fetch failed: %s", type(exc).__name__)
            return ""
        if r.status_code >= 400:
            return ""
        raw = r.text or ""
        # Drop scripts/styles
        raw = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
        raw = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", raw)
        # Prefer main content if present
        m = re.search(
            r'(?is)<main\b[^>]*>(.*?)</main>',
            raw,
        )
        if m:
            raw = m.group(1)
        return _strip_html(raw)

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
        text = text.strip()
        if len(text) <= max_chars:
            return [text] if text else []
        parts: list[str] = []
        # Prefer paragraph breaks
        paras = re.split(r"\n{2,}|(?<=\.)\s+(?=[A-ZА-ЯЁ])", text)
        buf = ""
        for p in paras:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) + 1 <= max_chars:
                buf = f"{buf} {p}".strip()
            else:
                if buf:
                    parts.append(buf)
                if len(p) <= max_chars:
                    buf = p
                else:
                    for i in range(0, len(p), max_chars):
                        parts.append(p[i : i + max_chars])
                    buf = ""
        if buf:
            parts.append(buf)
        return parts

    def retrieve(self, query: str, *, top_k: int = 5) -> list[BlogChunk]:
        tokens = _tokenize(query)
        if not tokens or not self._chunks:
            return []

        q_low = (query or "").lower()
        price_intent = any(
            w in q_low
            for w in (
                "цен",
                "прайс",
                "стоим",
                "сколько",
                "тариф",
                "руб",
                "₽",
                "price",
                "hour",
                "час",
                "пакет",
            )
        )

        scored: list[tuple[float, BlogChunk]] = []
        for ch in self._chunks:
            score = 0.0
            title_l = ch.title.lower()
            for t in tokens:
                if t in title_l:
                    score += 4.0
                # count occurrences in body
                c = ch.haystack.count(t)
                if c:
                    score += min(c, 5) * 1.0
            # Prefer price-list / llms chunks when user asks about cost.
            if price_intent and (
                "прайс" in title_l
                or "llms" in title_l
                or "цен" in title_l
                or "prays-list" in ch.url
                or "llms.txt" in ch.url
            ):
                score += 12.0
            if score > 0:
                scored.append((score, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        # Dedupe by post_id keeping best chunk
        seen: set[int] = set()
        out: list[BlogChunk] = []
        for _, ch in scored:
            if ch.post_id in seen:
                continue
            seen.add(ch.post_id)
            out.append(ch)
            if len(out) >= top_k:
                break
        return out

    async def ask(self, question: str) -> dict[str, Any]:
        await self.ensure_index()
        q = (question or "").strip()
        if not q:
            return {
                "answer": "Задайте вопрос по материалам блога.",
                "sources": [],
                "provider": "none",
                "demo_note": "empty",
            }

        hits = self.retrieve(q, top_k=5)
        if not hits:
            return {
                "answer": (
                    "В индексе блога не нашлось близких статей. "
                    "Попробуйте переформулировать (WordPress, VPS, бот, Директ, SSL…) "
                    "или откройте https://krivoshein.site/blog/"
                ),
                "sources": [],
                "provider": "none",
                "demo_note": "no_hits",
            }

        context_blocks = []
        sources = []
        for i, ch in enumerate(hits, 1):
            context_blocks.append(
                f"[{i}] {ch.title}\nURL: {ch.url}\n{ch.text[:900]}"
            )
            sources.append(
                {
                    "title": ch.title,
                    "url": ch.url,
                    "date": ch.date,
                    "snippet": ch.text[:220] + ("…" if len(ch.text) > 220 else ""),
                }
            )
        context = "\n\n".join(context_blocks)

        system = (
            "Ты демо-ассистент RAG по базе знаний krivoshein.site (ИП Кривошеин / Dr.Slon).\n"
            "В CONTEXT — фрагменты статей блога, прайс-листа и llms.txt.\n"
            "Отвечай ТОЛЬКО по CONTEXT. Цены называй только если они есть в CONTEXT "
            "(формулируй как ориентир «от … ₽», не оферта).\n"
            "Если цены/факта нет в CONTEXT — скажи, что в базе этого нет, "
            "и дай ссылку https://krivoshein.site/prays-list/ или /contacts/.\n"
            "В конце ответа перечисли источники номерами [1], [2]…\n"
            "Язык: русский. Кратко, по делу, 2–6 предложений.\n"
            "Не выдумывай цены и факты вне CONTEXT."
        )
        user_msg = f"CONTEXT:\n{context}\n\nQUESTION: {q}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        provider = "offline"
        answer = ""

        # Prefer GigaChat for this demo (product story).
        giga = self._get_giga()
        if giga is not None:
            try:
                answer = await giga.chat(
                    messages,
                    max_tokens=min(600, self._settings.llm_max_tokens + 100),
                    temperature=0.2,
                )
                provider = "gigachat"
            except LlmError as exc:
                logger.warning("Blog RAG GigaChat failed: %s", exc)
            except Exception:
                logger.exception("Blog RAG GigaChat unexpected")

        if not answer and self._settings.llm_enabled and self._settings.llm_api_key:
            try:
                llm = self._get_llm()
                answer = await llm.chat(
                    messages,
                    max_tokens=min(600, self._settings.llm_max_tokens + 100),
                    temperature=0.2,
                )
                provider = getattr(llm, "last_provider", None) or "groq"
            except LlmError as exc:
                logger.warning("Blog RAG LLM fallback failed: %s", exc)
            except Exception:
                logger.exception("Blog RAG LLM unexpected")

        if not answer:
            # Offline extractive fallback: show best snippets
            bullets = []
            for i, ch in enumerate(hits[:3], 1):
                bullets.append(f"[{i}] {ch.title}: {ch.text[:180]}…")
            answer = (
                "Сейчас модель недоступна — вот ближайшие фрагменты из блога:\n\n"
                + "\n".join(bullets)
                + "\n\nОткройте статьи по ссылкам ниже."
            )
            provider = "offline"

        return {
            "answer": answer,
            "sources": sources,
            "provider": provider,
            "demo_note": "rag_ok",
            "stats": {
                "posts_indexed": self._post_count,
                "chunks": len(self._chunks),
                "hits": len(hits),
            },
        }
