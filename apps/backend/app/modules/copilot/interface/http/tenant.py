from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import ensure_rls, tenant_id_from_request
from app.modules.copilot.services import (
    create_invoice_draft,
    create_order_draft,
    create_transfer_draft,
    query_readonly,
    suggest_overlay_fields,
)


def _feature_enabled() -> bool:
    value = str(os.getenv("COPILOT_TENANT_ENABLED", "1")).strip().lower()
    return value in ("1", "true", "yes", "on")


def _require_tenant_access(request: Request) -> dict[str, Any]:
    claims = getattr(request.state, "access_claims", None) or {}
    kind = str(claims.get("kind", "")).strip().lower()
    scope = str(claims.get("scope", "")).strip().lower()
    scopes_claim = claims.get("scopes")
    scopes: set[str] = set()
    if isinstance(scopes_claim, (list, tuple, set)):
        scopes = {str(s).strip().lower() for s in scopes_claim if s}
    elif isinstance(scopes_claim, str) and scopes_claim.strip():
        scopes = {scopes_claim.strip().lower()}

    if kind == "tenant" or scope == "tenant" or "tenant" in scopes:
        return claims

    # Fallback for legacy tokens that only carry tenant_id.
    if claims.get("tenant_id"):
        return claims

    raise HTTPException(status_code=403, detail="forbidden")


router = APIRouter(
    prefix="/ai",
    tags=["Copilot"],
    dependencies=[
        Depends(with_access_claims),
        Depends(_require_tenant_access),
        Depends(ensure_rls),
    ],
)


class AskIn(BaseModel):
    topic: str = Field(
        description="ventas_mes|ventas_por_almacen|top_productos|stock_bajo|pendientes_sri_sii|cobros_pagos"
    )
    params: dict[str, Any] | None = None


@router.post("/ask", response_model=dict[str, Any])
def ai_ask(payload: AskIn, db: Session = Depends(get_db)):
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    out = query_readonly(db, payload.topic, payload.params or {})
    # Masking is done inside service for PII fields
    return out


class ActIn(BaseModel):
    action: str = Field(
        description="create_invoice_draft|create_order_draft|create_transfer_draft|suggest_overlay_fields"
    )
    payload: dict[str, Any] | None = None


def _allow(action: str) -> bool:
    allowed = os.getenv(
        "COPILOT_ALLOWED_ACTIONS",
        "create_invoice_draft,create_order_draft,create_transfer_draft,suggest_overlay_fields",
    )
    set_allowed = {a.strip() for a in allowed.split(",") if a.strip()}
    return action in set_allowed


@router.post("/act", response_model=dict[str, Any])
def ai_act(payload: ActIn, request: Request, db: Session = Depends(get_db)):
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    if not _allow(payload.action):
        raise HTTPException(status_code=403, detail="action_not_allowed")

    if payload.action == "create_invoice_draft":
        claims = request.state.access_claims
        tenant_id = claims.get("tenant_id")
        if tenant_id is None or not str(tenant_id).isdigit():
            # In este backend convivimos con tenant_id mientras dura la transición
            raise HTTPException(status_code=400, detail="empresa_id_required_for_invoice")
        return create_invoice_draft(db, int(tenant_id), payload.payload or {})

    if payload.action == "create_order_draft":
        tid = tenant_id_from_request(request)
        return create_order_draft(db, payload.payload or {}, tenant_id=tid)

    if payload.action == "create_transfer_draft":
        tid = tenant_id_from_request(request)
        return create_transfer_draft(db, payload.payload or {}, tenant_id=tid)

    if payload.action == "suggest_overlay_fields":
        return suggest_overlay_fields(db)

    raise HTTPException(status_code=400, detail="unknown_action")
