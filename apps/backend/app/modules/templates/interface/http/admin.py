from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.audit_events import audit_event
from app.core.authz import require_scope
from app.modules.templates.services import validate_overlay

router = APIRouter(
    prefix="/admin/templates",
    tags=["Templates Admin"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("/packages", response_model=list[dict])
def list_packages(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT template_key, version FROM template_packages ORDER BY template_key, version")
    )
    return [{"template_key": r[0], "version": r[1]} for r in rows]


class AssignIn(BaseModel):
    tenant_id: str
    template_key: str
    version: int


@router.post("/assign", response_model=dict)
def assign_template(payload: AssignIn, request: Request, db: Session = Depends(get_db)):
    db.execute(
        text("""
            INSERT INTO tenant_templates(tenant_id, template_key, version, active)
            VALUES (CAST(:tid AS uuid), :key, :ver, true)
            ON CONFLICT (tenant_id, template_key)
            DO UPDATE SET version = EXCLUDED.version, active = true
            """),
        {"tid": payload.tenant_id, "key": payload.template_key, "ver": payload.version},
    )
    db.commit()
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="assign",
            entity_type="template_package",
            entity_id=str(payload.template_key),
            actor_type="user" if user_id else "system",
            source="admin_api",
            tenant_id=str(payload.tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"version": payload.version},
            req=request,
        )
    except Exception:
        pass
    return {"ok": True}


class OverlayIn(BaseModel):
    tenant_id: str
    name: str
    config: dict
    activate: bool | None = True


@router.post("/overlays", response_model=dict)
def create_overlay(payload: OverlayIn, request: Request, db: Session = Depends(get_db)):
    # Load or default limits
    lim = db.execute(
        text("SELECT limits FROM template_policies WHERE tenant_id=CAST(:tid AS uuid)"),
        {"tid": payload.tenant_id},
    ).scalar() or {"max_fields": 15, "max_bytes": 8192, "max_depth": 2}
    try:
        validate_overlay(payload.config, lim)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    row = db.execute(
        text("""
            INSERT INTO template_overlays(tenant_id, name, config, active)
            VALUES (CAST(:tid AS uuid), :name, :cfg::jsonb, :active)
            RETURNING id
            """),
        {
            "tid": payload.tenant_id,
            "name": payload.name,
            "cfg": payload.config,
            "active": bool(payload.activate),
        },
    ).first()
    db.commit()
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="create",
            entity_type="template_overlay",
            entity_id=str(row[0]) if row else None,
            actor_type="user" if user_id else "system",
            source="admin_api",
            tenant_id=str(payload.tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"name": payload.name, "active": bool(payload.activate)},
            req=request,
        )
    except Exception:
        pass
    return {"id": str(row[0])}


@router.post("/overlays/{overlay_id}/activate", response_model=dict)
def activate_overlay(overlay_id: str, request: Request, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT tenant_id FROM template_overlays WHERE id=CAST(:id AS uuid)"),
        {"id": overlay_id},
    ).first()
    db.execute(
        text("UPDATE template_overlays SET active=true WHERE id=CAST(:id AS uuid)"),
        {"id": overlay_id},
    )
    db.commit()
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="activate",
            entity_type="template_overlay",
            entity_id=str(overlay_id),
            actor_type="user" if user_id else "system",
            source="admin_api",
            tenant_id=str(row[0]) if row and row[0] else None,
            user_id=str(user_id) if user_id else None,
            changes={"active": True},
            req=request,
        )
    except Exception:
        pass
    return {"ok": True}
