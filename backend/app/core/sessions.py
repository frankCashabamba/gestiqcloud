"""
Server-side session middleware (demo en memoria).
Reemplaza con Redis/DB en producción.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from itsdangerous import Signer, BadSignature
import os, secrets, time

_MEMORY_STORE: dict[str, dict] = {}

class SessionMiddlewareServerSide(BaseHTTPMiddleware):
    def __init__(self, app, cookie_name: str, secret_key: str, https_only: bool = True):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.signer = Signer(secret_key)
        self.https_only = https_only

    async def dispatch(self, request: Request, call_next):
        raw = request.cookies.get(self.cookie_name)
        sid = None
        session = {}
        if raw:
            try:
                sid = self.signer.unsign(raw.encode()).decode()
                session = _MEMORY_STORE.get(sid, {})
            except BadSignature:
                pass

        request.state.session = session
        response: Response = await call_next(request)

        # Si se creó sesión nueva, persiste y setea cookie
        if getattr(request.state, "session_dirty", False) or (sid and session):
            if not sid:
                sid = secrets.token_urlsafe(32)
            _MEMORY_STORE[sid] = session | {"_updated": int(time.time())}
            signed = self.signer.sign(sid.encode()).decode()
            response.set_cookie(
                key=self.cookie_name, value=signed,
                httponly=True, secure=self.https_only, samesite="lax",
                path="/"
            )
        return response
