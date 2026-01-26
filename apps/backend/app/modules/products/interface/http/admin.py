from __future__ import annotations

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from fastapi import APIRouter, Depends

from apps.backend.app.shared.utils import ping_ok

router = APIRouter(
    prefix="/admin/products",
    tags=["Admin Products"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("/ping")
def ping_admin_products():
    return ping_ok()
