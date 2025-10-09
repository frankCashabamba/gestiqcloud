"""
Server-side session middleware backed by pluggable stores (Redis or in-memory).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from itsdangerous import Signer, BadSignature
import secrets
import time
import json


@dataclass
class SessionConfig:
    cookie_name: str
    ttl_seconds: int
    cookie_samesite: str = "Strict"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_domain: Optional[str] = None


class SessionStore(Protocol):
    async def create(self, sid: str, data: Dict[str, Any], ttl: int) -> None: ...
    async def get(self, sid: str) -> Dict[str, Any]: ...
    async def set(self, sid: str, data: Dict[str, Any], ttl: int) -> None: ...
    async def delete(self, sid: str) -> None: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}
        self._exp: Dict[str, int] = {}

    async def create(self, sid: str, data: Dict[str, Any], ttl: int) -> None:
        self._data[sid] = dict(data)
        self._exp[sid] = int(time.time()) + int(ttl)

    async def get(self, sid: str) -> Dict[str, Any]:
        now = int(time.time())
        exp = self._exp.get(sid)
        if exp is None or exp < now:
            self._data.pop(sid, None)
            self._exp.pop(sid, None)
            return {}
        return dict(self._data.get(sid, {}))

    async def set(self, sid: str, data: Dict[str, Any], ttl: int) -> None:
        self._data[sid] = dict(data)
        self._exp[sid] = int(time.time()) + int(ttl)

    async def delete(self, sid: str) -> None:
        self._data.pop(sid, None)
        self._exp.pop(sid, None)


class RedisSessionStore:
    def __init__(self, url: str, prefix: str = "sess:") -> None:
        try:
            from redis import asyncio as aioredis  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("redis-py is required for RedisSessionStore") from e
        self._redis = aioredis.from_url(url, decode_responses=True)
        self._prefix = prefix

    def _k(self, sid: str) -> str:
        return f"{self._prefix}{sid}"

    async def create(self, sid: str, data: Dict[str, Any], ttl: int) -> None:
        await self._redis.setex(self._k(sid), int(ttl), json.dumps(data))

    async def get(self, sid: str) -> Dict[str, Any]:
        raw = await self._redis.get(self._k(sid))
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    async def set(self, sid: str, data: Dict[str, Any], ttl: int) -> None:
        await self._redis.setex(self._k(sid), int(ttl), json.dumps(data))

    async def delete(self, sid: str) -> None:
        await self._redis.delete(self._k(sid))


class SessionMiddlewareServerSide(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        cookie_name: str,
        secret_key: str,
        https_only: bool = True,
        *,
        ttl_seconds: int = 60 * 60 * 4,
        store: Optional[SessionStore] = None,
        cookie_domain: Optional[str] = None,
    ):
        super().__init__(app)
        self.signer = Signer(secret_key)
        # Build config (respect settings when available)
        cookie_secure = https_only
        cookie_samesite = "Strict"
        cdomain = cookie_domain
        try:
            from app.config.settings import settings  # late import to avoid cycles

            # Prefer explicit settings over constructor defaults
            cookie_secure = bool(getattr(settings, "COOKIE_SECURE", https_only))
            raw_samesite = str(getattr(settings, "COOKIE_SAMESITE", "Strict")).lower()
            if raw_samesite not in ("lax", "strict", "none"):
                raw_samesite = "lax"
            cookie_samesite = raw_samesite.capitalize()  # store canonical, lower() on set_cookie
            if cdomain is None:
                cdomain = getattr(settings, "COOKIE_DOMAIN", None)
        except Exception:
            pass

        self.cfg = SessionConfig(
            cookie_name=cookie_name,
            ttl_seconds=ttl_seconds,
            cookie_secure=cookie_secure,
            cookie_samesite=cookie_samesite,
            cookie_httponly=True,
            cookie_domain=cdomain,
        )
        # Build store (prefer Redis when REDIS_URL present)
        if store is not None:
            self.store = store
        else:
            try:
                from app.config.settings import settings

                redis_url = getattr(settings, "REDIS_URL", None)
                if redis_url:
                    self.store = RedisSessionStore(redis_url)
                else:
                    self.store = InMemorySessionStore()
            except Exception:
                self.store = InMemorySessionStore()

    async def dispatch(self, request: Request, call_next):
        raw = request.cookies.get(self.cfg.cookie_name)
        sid = None
        session: Dict[str, Any] = {}
        if raw:
            try:
                sid = self.signer.unsign(raw.encode()).decode()
                session = await self.store.get(sid)
            except BadSignature:
                pass

        request.state.session = session
        response: Response = await call_next(request)

        # Persist session if it's dirty or a known sid with content
        if getattr(request.state, "session_dirty", False) or (sid and request.state.session):
            if not sid:
                sid = secrets.token_urlsafe(32)
            await self.store.set(sid, dict(request.state.session), self.cfg.ttl_seconds)
            signed = self.signer.sign(sid.encode()).decode()
            response.set_cookie(
                key=self.cfg.cookie_name,
                value=signed,
                httponly=self.cfg.cookie_httponly,
                secure=self.cfg.cookie_secure,
                samesite=self.cfg.cookie_samesite.lower(),
                path="/",
                domain=self.cfg.cookie_domain,
            )
        return response
