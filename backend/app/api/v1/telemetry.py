from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel


logger = logging.getLogger("app.telemetry")
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryEvent(BaseModel):
    event: str
    data: Optional[Dict[str, Any]] = None
    ts: Optional[float] = None


@router.post("/event", status_code=202)
async def ingest_event(payload: TelemetryEvent, request: Request):
    req_id = getattr(getattr(request, "state", object()), "request_id", None)
    client_rev = request.headers.get("X-Client-Revision")
    client_ver = request.headers.get("X-Client-Version")
    try:
        logger.info(
            json.dumps(
                {
                    "event": payload.event,
                    "data": payload.data or {},
                    "ts": payload.ts,
                    "req_id": req_id,
                    "client_rev": client_rev,
                    "client_ver": client_ver,
                    "ip": request.client.host if request.client else None,
                    "ua": request.headers.get("user-agent"),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    except Exception:
        # never fail telemetry
        pass
    return {"accepted": True}

