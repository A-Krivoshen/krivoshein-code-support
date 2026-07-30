"""Web AI Popup Assistant — public chat API + static widget."""

from __future__ import annotations

__all__ = ["create_web_router"]


def create_web_router():
    from app.web.router import router

    return router
