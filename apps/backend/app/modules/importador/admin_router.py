from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

from .schemas import (
    RoutingPreviewDocumentOut,
    RoutingPreviewRequest,
    RoutingPreviewResponse,
    RoutingProfileAdminIn,
    RoutingProfileAdminOut,
    RoutingRuleAdminIn,
    RoutingRuleAdminOut,
)
from .services.document_routing_admin_service import (
    create_routing_profile,
    create_routing_rule,
    delete_routing_profile,
    delete_routing_rule,
    list_preview_documents,
    list_routing_profiles,
    list_routing_rules,
    preview_routing_decision,
    update_routing_profile,
    update_routing_rule,
)

router = APIRouter(
    prefix="/admin/importador/routing",
    tags=["admin:importador:routing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("/profiles", response_model=list[RoutingProfileAdminOut])
def get_routing_profiles(db: Session = Depends(get_db)):
    return list_routing_profiles(db)


@router.post("/profiles")
def post_routing_profile(payload: RoutingProfileAdminIn, db: Session = Depends(get_db)):
    return {"ok": True, "item": create_routing_profile(db, payload)}


@router.put("/profiles/{profile_code}")
def put_routing_profile(
    profile_code: str,
    payload: RoutingProfileAdminIn,
    db: Session = Depends(get_db),
):
    return {"ok": True, "item": update_routing_profile(db, profile_code, payload)}


@router.delete("/profiles/{profile_code}")
def remove_routing_profile(profile_code: str, db: Session = Depends(get_db)):
    return delete_routing_profile(db, profile_code)


@router.get("/rules", response_model=list[RoutingRuleAdminOut])
def get_routing_rules(
    scope_kind: str | None = Query(default=None, pattern="^(system|sector|tenant)$"),
    db: Session = Depends(get_db),
):
    return list_routing_rules(db, scope_kind=scope_kind)


@router.post("/rules")
def post_routing_rule(payload: RoutingRuleAdminIn, db: Session = Depends(get_db)):
    return {"ok": True, "item": create_routing_rule(db, payload)}


@router.put("/rules/{rule_id}")
def put_routing_rule(
    rule_id: UUID,
    payload: RoutingRuleAdminIn,
    db: Session = Depends(get_db),
):
    return {"ok": True, "item": update_routing_rule(db, rule_id, payload)}


@router.delete("/rules/{rule_id}")
def remove_routing_rule(rule_id: UUID, db: Session = Depends(get_db)):
    return delete_routing_rule(db, rule_id)


@router.post("/preview", response_model=RoutingPreviewResponse)
def post_routing_preview(payload: RoutingPreviewRequest, db: Session = Depends(get_db)):
    return preview_routing_decision(db, payload)


@router.get("/documents", response_model=list[RoutingPreviewDocumentOut])
def get_preview_documents(
    tenant_id: UUID,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=12, ge=1, le=25),
    db: Session = Depends(get_db),
):
    return list_preview_documents(db, tenant_id=tenant_id, q=q, limit=limit)
