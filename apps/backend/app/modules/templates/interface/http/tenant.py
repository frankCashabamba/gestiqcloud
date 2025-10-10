from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.templates.services import deep_merge

router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.get("/ui-config", response_model=dict)
def ui_config(request: Request, db: Session = Depends(get_db)):
    # Resolve package for tenant
    row = db.execute(
        text(
            """
            SELECT tp.config AS pkg
            FROM tenant_templates tt
            JOIN template_packages tp ON tp.template_key = tt.template_key AND tp.version = tt.version
            WHERE tt.tenant_id = current_setting('app.tenant_id', true)::uuid AND tt.active
            """
        )
    ).first()
    base = row[0] if row and row[0] else {}

    # Apply active overlays (in insertion order)
    overs = db.execute(
        text(
            "SELECT config FROM template_overlays WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND active ORDER BY created_at ASC"
        )
    ).fetchall()
    composed = dict(base)
    for r in overs:
        composed = deep_merge(composed, r[0])
    return composed

