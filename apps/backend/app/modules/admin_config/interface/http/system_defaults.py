"""Admin endpoints — CRUD de defaults globales del sistema."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.services.system_defaults_service import list_system_defaults, update_system_default

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))])


class SystemDefaultUpdate(BaseModel):
    value: str


@router.get("/config/system-defaults")
def get_system_defaults(
    db: Session = Depends(get_db),
):
    return list_system_defaults(db)


@router.put("/config/system-defaults/{key:path}")
def put_system_default(
    key: str,
    payload: SystemDefaultUpdate,
    db: Session = Depends(get_db),
):
    updated = update_system_default(db, key, payload.value)
    if updated is None:
        raise HTTPException(404, f"Clave '{key}' no encontrada en system_defaults")
    return updated
