from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")


def _json(obj: dict[str, Any]) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(obj)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        client_rev = request.headers.get("X-Client-Revision")
        client_ver = request.headers.get("X-Client-Version")
        # expone en request.state y propaga en respuesta
        try:
            request.state.request_id = req_id
        except Exception:
            pass

        resp: Response = await call_next(request)

        dur_ms = int((time.perf_counter() - start) * 1000)
        resp.headers.setdefault("X-Request-ID", req_id)
        if client_rev:
            resp.headers.setdefault("X-Client-Revision", client_rev)
        if client_ver:
            resp.headers.setdefault("X-Client-Version", client_ver)

        try:
            # Try to include tenant/user from access_claims
            tenant_id = None
            user_id = None
            try:
                claims = getattr(request.state, "access_claims", None) or {}
                if isinstance(claims, dict):
                    tenant_id = claims.get("tenant_id")
                    user_id = claims.get("user_id")
            except Exception:
                pass

            logger.info(
                _json(
                    {
                        "level": "info",
                        "req_id": req_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": resp.status_code,
                        "dur_ms": dur_ms,
                        "ip": request.client.host if request.client else None,
                        "ua": request.headers.get("user-agent"),
                        "client_rev": client_rev,
                        "client_ver": client_ver,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                    }
                )
            )
        except Exception:
            # no interrumpir el ciclo por logging
            pass

        return resp
