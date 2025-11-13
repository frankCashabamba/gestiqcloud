from __future__ import annotations

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.modules.templates.services import validate_overlay
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

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
def assign_template(payload: AssignIn, db: Session = Depends(get_db)):
    db.execute(
        text(
            """
            INSERT INTO tenant_templates(tenant_id, template_key, version, active)
            VALUES (CAST(:tid AS uuid), :key, :ver, true)
            ON CONFLICT (tenant_id, template_key)
            DO UPDATE SET version = EXCLUDED.version, active = true
            """
        ),
        {"tid": payload.tenant_id, "key": payload.template_key, "ver": payload.version},
    )
    db.commit()
    return {"ok": True}


class OverlayIn(BaseModel):
    tenant_id: str
    name: str
    config: dict
    activate: bool | None = True


@router.post("/overlays", response_model=dict)
def create_overlay(payload: OverlayIn, db: Session = Depends(get_db)):
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
        text(
            """
            INSERT INTO template_overlays(tenant_id, name, config, active)
            VALUES (CAST(:tid AS uuid), :name, :cfg::jsonb, :active)
            RETURNING id
            """
        ),
        {
            "tid": payload.tenant_id,
            "name": payload.name,
            "cfg": payload.config,
            "active": bool(payload.activate),
        },
    ).first()
    db.commit()
    return {"id": str(row[0])}


@router.post("/overlays/{overlay_id}/activate", response_model=dict)
def activate_overlay(overlay_id: str, db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE template_overlays SET active=true WHERE id=CAST(:id AS uuid)"),
        {"id": overlay_id},
    )
    db.commit()
    return {"ok": True}
