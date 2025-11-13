from __future__ import annotations

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
    # Silent accept - no logging to avoid spam
    return {"accepted": True}
