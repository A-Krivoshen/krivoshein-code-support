"""Fallback price replies must include Flask from 50 000 ₽, not 90 000 ₽."""

from __future__ import annotations

from app.web.knowledge import SITE_PROFILES, profile_for_host
from app.web.service import WebAssistantService


class _DummyStore:
    pass


def _svc() -> WebAssistantService:
    return WebAssistantService.__new__(WebAssistantService)


def test_flask_profile_exists():
    profile = profile_for_host("flask.krivoshein.site")
    assert profile["key"] == "flask"
    assert "50 000" in str(profile["greeting"])
    assert "https://flask.krivoshein.site" not in SITE_PROFILES  # keys are hostnames
    assert "flask.krivoshein.site" in SITE_PROFILES


def test_detect_flask_not_wordpress():
    svc = _svc()
    assert svc._detect_service_key("сколько стоит сайт на flask?") == "flask"
    assert svc._detect_service_key("нужен сайт на Python") == "flask"
    assert svc._detect_service_key("лендинг на фласк") == "flask"
    assert svc._detect_service_key("корпоративный сайт на wordpress") == "wordpress"


def test_flask_price_is_50000_not_90000():
    svc = _svc()
    reply = svc._fallback_service_reply(
        "сколько стоит сайт на flask?", "Услуги Dr.Slon", en=False, price_focus=True
    )
    assert reply is not None
    assert "50 000" in reply
    assert "https://flask.krivoshein.site" in reply
    assert "90 000" not in reply


def test_price_list_includes_flask():
    svc = _svc()
    reply = svc._fallback_service_reply(
        "прайс", "Услуги Dr.Slon", en=False, price_focus=True
    )
    assert reply is not None
    assert "Flask" in reply
    assert "50 000" in reply
    # Corporate WordPress stays 90 000 in the general list, not as Flask.
    assert "корп. сайт от 90 000" in reply
