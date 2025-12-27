from __future__ import annotations

import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    from redis import asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, redis_url: str | None = None, limit_per_minute: int = 120):
        super().__init__(app)
        self.limit = max(1, int(limit_per_minute))
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.redis = None

    async def _get_redis(self):
        if self.redis is None and self.redis_url and aioredis is not None:
            self.redis = aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        return self.redis

    async def dispatch(self, request: Request, call_next):
        # Skip health
        if request.url.path in ("/health", "/healthz", "/"):
            return await call_next(request)

        # Skip admin config/catalog endpoints in dev to avoid throttling the Admin UI bootstrap
        try:
            path = request.url.path or ""
            if path.startswith("/api/v1/admin/config"):
                return await call_next(request)
        except Exception:
            pass

        # Exempt large-file chunked upload endpoints from generic rate limiting
        # to allow many small requests during a single file upload.
        try:
            path = request.url.path or ""
            if path.startswith(
                ("/api/v1/imports/uploads/chunk", "/api/v1/tenant/imports/uploads/chunk")
            ):
                return await call_next(request)
        except Exception:
            pass

        # If no Redis, allow
        r = await self._get_redis()
        if r is None:
            return await call_next(request)

        try:
            # Build key: prefer user_id, fallback tenant_id, then IP
            user_id = None
            tenant_id = None
            claims = getattr(request.state, "access_claims", None) or {}
            if isinstance(claims, dict):
                user_id = claims.get("user_id")
                tenant_id = claims.get("tenant_id")
            ident = user_id or tenant_id or (request.client.host if request.client else "anon")
            bucket = int(time.time() // 60)  # per-minute window
            key = f"rl:{ident}:{bucket}"
            ttl = 120  # seconds (1m window + slack)
            # Increment and set TTL atomically via pipeline
            async with r.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, ttl)
                count, _ = await pipe.execute()
            if int(count) > self.limit:
                return JSONResponse({"detail": "rate_limit_exceeded"}, status_code=429)
        except Exception:
            # Fail-open on limiter errors
            return await call_next(request)

        return await call_next(request)
