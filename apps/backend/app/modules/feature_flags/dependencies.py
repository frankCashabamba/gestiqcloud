"""FastAPI dependencies for feature flags."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.db.rls import tenant_id_from_request

from .service import ResolvedFlags, get_tenant_flags, resolve_flags


def get_feature_flags(
    request: Request,
    db: Session = Depends(get_db),
) -> ResolvedFlags:
    tenant_id = tenant_id_from_request(request)
    if tenant_id:
        return get_tenant_flags(db, tenant_id)
    return resolve_flags()


def require_flag(flag_name: str):
    def _check(flags: ResolvedFlags = Depends(get_feature_flags)):
        if not flags.is_enabled(flag_name):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{flag_name}' is not enabled for this tenant",
            )
        return flags

    return _check
