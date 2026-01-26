"""Middleware to extract language preference from request."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from . import get_lang_from_header


class I18nMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts language from Accept-Language header."""

    async def dispatch(self, request: Request, call_next):
        accept_lang = request.headers.get("Accept-Language")
        request.state.lang = get_lang_from_header(accept_lang)
        return await call_next(request)
