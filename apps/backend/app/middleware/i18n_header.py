# app/middleware/i18n_header.py
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.i18n import detect_lang

class ContentLanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        try:
            resp.headers["Content-Language"] = detect_lang(request)
        except Exception:
            pass
        return resp
