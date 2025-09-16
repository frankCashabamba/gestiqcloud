from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope


router = APIRouter(
    prefix="/admin/productos",
    tags=["Admin Productos"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("/ping")
def ping_admin_productos():
    return {"ok": True}

