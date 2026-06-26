from __future__ import annotations

import httpx
import pytest

from app.max_api.client import MaxApiClient
from app.max_api.exceptions import MaxApiRequestError, MaxApiResponseError


@pytest.fixture
def client():
    return MaxApiClient("test-token", base_url="https://api.test")


async def test_get_me_success(client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "test-token"
        return httpx.Response(200, json={"user_id": 1, "name": "Support Bot"})

    transport = httpx.MockTransport(handler)
    client.http = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.test",
        headers={"Authorization": "test-token"},
    )

    bot = await client.get_me()
    assert bot.user_id == 1
    assert bot.name == "Support Bot"


async def test_get_me_invalid_response(client):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"name": "No ID"})
    )
    client.http = httpx.AsyncClient(transport=transport, base_url="https://api.test")

    with pytest.raises(MaxApiResponseError):
        await client.get_me()


async def test_request_http_error(client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    client.http = httpx.AsyncClient(transport=transport, base_url="https://api.test")

    with pytest.raises(MaxApiRequestError, match="transport error"):
        await client.get_me()


async def test_send_message_strips_notify_for_channel(client):
    import json

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"message": {"mid": "1", "text": "ok"}})

    transport = httpx.MockTransport(handler)
    client.http = httpx.AsyncClient(transport=transport, base_url="https://api.test")

    await client.send_message(-100, "hello", notify=False)

    assert "notify" not in captured["body"]


async def test_forward_ticket_image_requires_token(client):
    with pytest.raises(MaxApiRequestError, match="token is required"):
        await client.forward_ticket_image(-100, token="   ")