from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls


router = APIRouter(
    prefix="/facturae",
    tags=["Facturae"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.get("/ping")
def ping_facturae():
    return {"ok": True}

