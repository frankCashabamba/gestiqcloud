from __future__ import annotations

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics.store import record as record_metric


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        resp: Response = await call_next(request)
        dur_ms = int((time.perf_counter() - start) * 1000)
        try:
            record_metric(request.method, request.url.path, resp.status_code, dur_ms)
        except Exception:
            # nunca romper la request por métricas
            pass
        return resp
