from __future__ import annotations

from apps.backend.app.shared.utils import ping_ok
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
    return ping_ok()
