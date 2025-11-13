from __future__ import annotations

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls, tenant_id_from_request, tenant_id_sql_expr
from app.modules.templates.services import deep_merge
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("/ui-config", response_model=dict)
def ui_config(request: Request, db: Session = Depends(get_db)):
    # Resolve package for tenant
    tid = tenant_id_from_request(request)
    row = db.execute(
        text(
            """
            SELECT tp.config AS pkg
            FROM tenant_templates tt
            JOIN template_packages tp ON tp.template_key = tt.template_key AND tp.version = tt.version
            WHERE tt.tenant_id = """
            + tenant_id_sql_expr()
            + """ AND tt.active
            """
        ),
        {"tid": tid},
    ).first()
    base = row[0] if row and row[0] else {}

    # Apply active overlays (in insertion order)
    overs = db.execute(
        text(
            "SELECT config FROM template_overlays WHERE tenant_id = "
            + tenant_id_sql_expr()
            + " AND active ORDER BY created_at ASC"
        ),
        {"tid": tid},
    ).fetchall()
    composed = dict(base)
    for r in overs:
        composed = deep_merge(composed, r[0])
    return composed
