"""Tests for Groq → GigaChat failover and GigaChat OAuth token cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.llm.client import LlmClient, LlmRequestError
from app.llm.gigachat import GigaChatClient


class _Cfg:
    """Minimal settings stand-in for unit tests."""

    llm_enabled = True
    llm_api_key = "groq-test-key"
    llm_base_url = "https://api.groq.com/openai/v1"
    llm_model = "llama-test"
    llm_timeout = 5.0
    llm_max_tokens = 100
    llm_temperature = 0.3

    gigachat_enabled = True
    gigachat_client_id = "client-id"
    gigachat_auth_key = "dGVzdDprZXk="  # base64 test:key
    gigachat_scope = "GIGACHAT_API_PERS"
    gigachat_model = "GigaChat-2-Pro"
    gigachat_base_url = "https://api.giga.chat/v1"
    gigachat_oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_timeout = 5.0
    gigachat_verify_ssl = True


def _json_response(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=payload,
        request=httpx.Request("POST", "https://example.test"),
    )


@pytest.mark.asyncio
async def test_gigachat_token_is_cached():
    cfg = _Cfg()
    client = GigaChatClient(cfg)  # type: ignore[arg-type]
    call_count = {"n": 0}

    async def fake_post(url, **kwargs):
        call_count["n"] += 1
        return _json_response(
            200,
            {
                "access_token": "token-abc",
                "expires_at": 9_999_999_999,  # far future (seconds)
            },
        )

    client._http.post = fake_post  # type: ignore[method-assign]

    t1 = await client.get_access_token()
    t2 = await client.get_access_token()
    assert t1 == t2 == "token-abc"
    assert call_count["n"] == 1

    await client.aclose()


@pytest.mark.asyncio
async def test_gigachat_token_force_refresh():
    cfg = _Cfg()
    client = GigaChatClient(cfg)  # type: ignore[arg-type]
    tokens = iter(["token-1", "token-2"])
    call_count = {"n": 0}

    async def fake_post(url, **kwargs):
        call_count["n"] += 1
        return _json_response(
            200,
            {"access_token": next(tokens), "expires_at": 9_999_999_999},
        )

    client._http.post = fake_post  # type: ignore[method-assign]

    assert await client.get_access_token() == "token-1"
    assert await client.get_access_token(force_refresh=True) == "token-2"
    assert call_count["n"] == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_failover_groq_to_gigachat():
    cfg = _Cfg()
    giga = MagicMock()
    giga.is_configured = True
    giga.chat = AsyncMock(return_value="ответ от gigachat")
    giga.aclose = AsyncMock()

    client = LlmClient(cfg, gigachat=giga)  # type: ignore[arg-type]

    async def groq_fail(url, **kwargs):
        return _json_response(429, {"error": "rate_limit"})

    client._http.post = groq_fail  # type: ignore[method-assign]

    messages = [{"role": "user", "content": "привет"}]
    text = await client.chat(messages)
    assert text == "ответ от gigachat"
    assert client.last_provider == "gigachat"
    giga.chat.assert_awaited_once()
    # GigaChat must receive its own model, not Groq's
    assert giga.chat.await_args.kwargs.get("model") == "GigaChat-2-Pro" or (
        giga.chat.await_args.args and True
    )
    # model is passed via kwargs in client
    call_kwargs = giga.chat.await_args.kwargs
    assert call_kwargs["model"] == "GigaChat-2-Pro"

    await client.aclose()


@pytest.mark.asyncio
async def test_primary_groq_success_skips_gigachat():
    cfg = _Cfg()
    giga = MagicMock()
    giga.is_configured = True
    giga.chat = AsyncMock(return_value="should-not-call")
    giga.aclose = AsyncMock()

    client = LlmClient(cfg, gigachat=giga)  # type: ignore[arg-type]

    async def groq_ok(url, **kwargs):
        return _json_response(
            200,
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "ответ groq"}}
                ]
            },
        )

    client._http.post = groq_ok  # type: ignore[method-assign]

    text = await client.chat([{"role": "user", "content": "hi"}])
    assert text == "ответ groq"
    assert client.last_provider == "groq"
    giga.chat.assert_not_awaited()
    await client.aclose()


@pytest.mark.asyncio
async def test_both_providers_fail_raises():
    cfg = _Cfg()
    giga = MagicMock()
    giga.is_configured = True
    giga.chat = AsyncMock(side_effect=LlmRequestError("giga down", status_code=500))
    giga.aclose = AsyncMock()

    client = LlmClient(cfg, gigachat=giga)  # type: ignore[arg-type]

    async def groq_fail(url, **kwargs):
        return _json_response(503, {"error": "unavailable"})

    client._http.post = groq_fail  # type: ignore[method-assign]

    with pytest.raises(LlmRequestError):
        await client.chat([{"role": "user", "content": "x"}])
    giga.chat.assert_awaited_once()
    await client.aclose()


@pytest.mark.asyncio
async def test_gigachat_disabled_no_fallback():
    cfg = _Cfg()
    cfg.gigachat_enabled = False
    giga = MagicMock()
    giga.is_configured = False
    giga.chat = AsyncMock()
    giga.aclose = AsyncMock()

    client = LlmClient(cfg, gigachat=giga)  # type: ignore[arg-type]

    async def groq_fail(url, **kwargs):
        return _json_response(429, {"error": "rate_limit"})

    client._http.post = groq_fail  # type: ignore[method-assign]

    with pytest.raises(LlmRequestError) as ei:
        await client.chat([{"role": "user", "content": "x"}])
    assert ei.value.status_code == 429
    giga.chat.assert_not_awaited()
    await client.aclose()
