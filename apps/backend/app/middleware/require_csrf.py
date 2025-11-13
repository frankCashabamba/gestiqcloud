# app/middleware/require_csrf.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

SAFE = {"GET", "HEAD", "OPTIONS"}

# Exenciones por **sufijo** para que funcionen con prefijos como /api/v1 y /api/v1/tenant
EXEMPT_SUFFIXES = ("/auth/login", "/auth/refresh", "/auth/logout")

HEADER_NAMES = ("X-CSRF-Token", "X-CSRF")  # acepta ambos


class RequireCSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        method = request.method.upper()
        path = request.url.path

        # Métodos seguros: no requieren CSRF
        if method in SAFE:
            return await call_next(request)

        # Exenciones por sufijo (sirve para /api/v1/admin/auth/login y /api/v1/tenant/auth/login)
        if path.endswith(EXEMPT_SUFFIXES):
            return await call_next(request)

        # Lee cookie, session y header
        cookie = request.cookies.get("csrf_token")
        session_token = getattr(getattr(request, "state", object()), "session", {}).get("csrf")
        sent = None
        for hname in HEADER_NAMES:
            v = request.headers.get(hname)
            if v:
                sent = v
                break

        ok = False
        # Coincide con sesión (si existe)
        if sent and session_token and sent == session_token:
            ok = True
        # O coincide con cookie (double-submit)
        elif sent and cookie and sent == cookie:
            ok = True

        if not ok:
            return JSONResponse({"detail": "CSRF token missing/invalid"}, status_code=403)

        return await call_next(request)
