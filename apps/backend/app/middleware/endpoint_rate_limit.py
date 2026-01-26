"""
Middleware de rate limiting por endpoint.
Implementa protección específica para endpoints críticos (login, reset password, etc.)
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.rate_limit")


class EndpointRateLimiter(BaseHTTPMiddleware):
    """
    Rate limiter configurable por endpoint.

    Uso:
        app.add_middleware(
            EndpointRateLimiter,
            limits={
                "/api/v1/tenant/auth/login": (10, 60),  # 10 req/min
                "/api/v1/tenant/auth/password-reset": (5, 300),  # 5 req/5min
            }
        )
    """

    def __init__(
        self,
        app,
        limits: dict[str, tuple[int, int]] | None = None,
        key_func: Callable[[Request], str] | None = None,
    ):
        super().__init__(app)
        # limits = {endpoint: (max_requests, window_seconds)}
        self.limits = limits or self._default_limits()
        self.key_func = key_func or self._default_key_func
        # Storage: {key: [(timestamp, endpoint), ...]}
        self._store: dict[str, list[tuple[float, str]]] = defaultdict(list)

    @staticmethod
    def _default_limits() -> dict[str, tuple[int, int]]:
        """Límites por defecto para endpoints críticos"""
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
        """Extrae clave para rate limit (por IP)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, key: str, window: int) -> None:
        """Elimina requests fuera de la ventana de tiempo"""
        now = time.time()
        if key in self._store:
            self._store[key] = [(ts, ep) for ts, ep in self._store[key] if now - ts < window]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Solo aplicar rate limit si el endpoint está en la lista
        if path not in self.limits:
            return await call_next(request)

        max_requests, window = self.limits[path]
        key = self.key_func(request)
        unique_key = f"{key}:{path}"

        # Limpiar requests antiguos
        self._clean_old_requests(unique_key, window)

        # Contar requests en ventana actual
        now = time.time()
        current_requests = [
            ts for ts, ep in self._store[unique_key] if now - ts < window and ep == path
        ]

        if len(current_requests) >= max_requests:
            # Rate limit excedido
            retry_after = int(window - (now - current_requests[0])) + 1
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "key": key,
                    "path": path,
                    "requests": len(current_requests),
                    "max": max_requests,
                    "window": window,
                    "retry_after": retry_after,
                },
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

        # Registrar request
        self._store[unique_key].append((now, path))

        # Continuar con la request
        response = await call_next(request)

        # Agregar headers informativos
        remaining = max_requests - len(current_requests) - 1
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Window"] = str(window)

        return response


# Decorador alternativo para uso en routers específicos
def rate_limit(max_requests: int, window: int):
    """
    Decorador para aplicar rate limit a un endpoint específico.

    Uso:
        @router.post("/login")
        @rate_limit(10, 60)  # 10 req/min
        async def login(...):
            ...
    """
    # Store local por endpoint
    _store: dict[str, list[float]] = defaultdict(list)

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Extraer IP
            forwarded = request.headers.get("X-Forwarded-For")
            ip = (
                forwarded.split(",")[0].strip()
                if forwarded
                else (request.client.host if request.client else "unknown")
            )

            # Limpiar requests viejos
            now = time.time()
            _store[ip] = [ts for ts in _store[ip] if now - ts < window]

            # Verificar límite
            if len(_store[ip]) >= max_requests:
                retry_after = int(window - (now - _store[ip][0])) + 1
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Too many requests. Try again in {retry_after}s",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # Registrar y ejecutar
            _store[ip].append(now)
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
