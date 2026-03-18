"""Inventory — Expiry/Caducidad alerts endpoints."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.modules.inventory.application.expiry_alerts import ExpiryAlertService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inventory/expiry",
    tags=["Inventory – Expiry Alerts"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {}) or {}
    tid = claims.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id_not_found")
    return UUID(str(tid))


@router.get("/alerts", response_model=list[dict[str, Any]])
def get_expiry_alerts(
    request: Request,
    days_ahead: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Retorna productos/lotes que vencen dentro de los próximos N días."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    return ExpiryAlertService.check_expiring_products(db, str(tenant_id), days_ahead=days_ahead)


@router.get("/expired", response_model=list[dict[str, Any]])
def get_expired_products(
    request: Request,
    db: Session = Depends(get_db),
):
    """Retorna productos/lotes ya vencidos que aún tienen stock."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    return ExpiryAlertService.check_expired_products(db, str(tenant_id))


@router.get("/summary", response_model=dict[str, Any])
def get_expiry_summary(
    request: Request,
    db: Session = Depends(get_db),
):
    """Retorna resumen de caducidad para el dashboard."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    return ExpiryAlertService.get_expiry_summary(db, str(tenant_id))
