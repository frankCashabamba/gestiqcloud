"""Rate limiting por endpoint (capa oficial para endpoints críticos).

Protege endpoints concretos (login, password-reset, etc.) con límites
declarativos `{ruta: (max_requests, window_seconds)}`.

Storage: **Redis** si `REDIS_URL` está disponible (consistente entre procesos
uvicorn/Celery), con **fallback a memoria local** si no hay Redis (p.ej. tests).
Usar memoria local en producción multi-proceso permitiría evadir el límite
repartiendo requests entre procesos, por eso Redis es el modo preferente.

Arquitectura de rate limiting del backend (ver docs/seguridad.md):
  - `RateLimitMiddleware`  → límite GLOBAL de tráfico por user/tenant/IP (Redis).
  - `EndpointRateLimiter`  → límites por endpoint crítico (esta clase).
  - `SimpleRateLimiter` / `core/login_rate_limit` → lockout anti-fuerza-bruta por
    fallos de login (Redis). Propósito distinto (cuenta fallos, no requests).
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from redis import asyncio as aioredis
except Exception:  # pragma: no cover - redis optional
    aioredis = None

logger = logging.getLogger("app.rate_limit")


class EndpointRateLimiter(BaseHTTPMiddleware):
    """Rate limiter configurable por endpoint con backend Redis (+ fallback memoria)."""

    def __init__(
        self,
        app,
        limits: dict[str, tuple[int, int]] | None = None,
        key_func: Callable[[Request], str] | None = None,
        redis_url: str | None = None,
    ):
        super().__init__(app)
        # limits = {endpoint: (max_requests, window_seconds)}
        self.limits = limits or self._default_limits()
        self.key_func = key_func or self._default_key_func
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.redis = None
        # Fallback en memoria: {key: [(timestamp, endpoint), ...]}
        self._store: dict[str, list[tuple[float, str]]] = defaultdict(list)

    @staticmethod
    def _default_limits() -> dict[str, tuple[int, int]]:
        """Límites por defecto para endpoints críticos."""
        return {
            "/api/v1/tenant/auth/login": (10, 60),  # 10 intentos/min
            "/api/v1/admin/auth/login": (10, 60),
            "/api/v1/auth/login": (10, 60),
            "/api/v1/tenant/auth/password-reset": (5, 300),  # 5 req/5min
            "/api/v1/tenant/auth/password-reset-confirm": (5, 300),
            "/api/v1/admin/users": (30, 60),  # 30 req/min
            "/api/v1/admin/companies": (20, 60),
        }

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Extrae clave para rate limit (por IP, respetando proxy)."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _get_redis(self):
        if self.redis is None and self.redis_url and aioredis is not None:
            try:
                self.redis = aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
            except Exception:
                self.redis = None
        return self.redis

    async def _check_redis(
        self, r, key: str, path: str, max_requests: int, window: int
    ) -> tuple[bool, int, int]:
        """Fixed-window counter en Redis. Devuelve (allowed, retry_after, remaining)."""
        now = int(time.time())
        bucket = now // window
        rkey = f"erl:{key}:{path}:{bucket}"
        async with r.pipeline(transaction=True) as pipe:
            pipe.incr(rkey)
            pipe.expire(rkey, window + 5)
            count, _ = await pipe.execute()
        count = int(count)
        if count > max_requests:
            retry_after = window - (now % window) + 1
            return False, retry_after, 0
        return True, 0, max(0, max_requests - count)

    def _check_memory(
        self, key: str, path: str, max_requests: int, window: int
    ) -> tuple[bool, int, int]:
        """Sliding-window en memoria local (fallback sin Redis)."""
        now = time.time()
        unique_key = f"{key}:{path}"
        self._store[unique_key] = [
            (ts, ep) for ts, ep in self._store[unique_key] if now - ts < window
        ]
        current = [ts for ts, ep in self._store[unique_key] if ep == path]
        if len(current) >= max_requests:
            retry_after = int(window - (now - current[0])) + 1
            return False, retry_after, 0
        self._store[unique_key].append((now, path))
        return True, 0, max(0, max_requests - len(current) - 1)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Solo aplicar rate limit si el endpoint está en la lista
        if path not in self.limits:
            return await call_next(request)

        max_requests, window = self.limits[path]
        key = self.key_func(request)

        try:
            r = await self._get_redis()
            if r is not None:
                allowed, retry_after, remaining = await self._check_redis(
                    r, key, path, max_requests, window
                )
            else:
                allowed, retry_after, remaining = self._check_memory(
                    key, path, max_requests, window
                )
        except Exception:
            # Fail-open ante errores del limiter (no bloquear tráfico legítimo)
            return await call_next(request)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                extra={"key": key, "path": path, "max": max_requests, "window": window},
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
        return response
