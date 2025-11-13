"""
Compatibility shim for RLS-related dependencies expected by routers.

Historically, routers imported `app.middleware.rls` for `ensure_rls` and
`get_current_tenant_id`. The internal implementation was refactored to
`app.db.rls`, but some routers still reference the old path. This module
bridges that gap and preserves the previous public API.
"""

from __future__ import annotations

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db import rls as rls_core
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session


def ensure_rls(request: Request, db: Session = Depends(get_db)) -> str:
    """Ensures RLS GUCs are set and returns the tenant UUID as str.

    - Validates access token and stores claims on the request
    - Calls the core RLS setup to set session GUCs
    - Returns the resolved tenant UUID string
    """
    # Populate request.state.access_claims (raises 401 on failure)
    _claims = with_access_claims(request)

    # Set session GUCs (non-fatal if something goes wrong inside)
    rls_core.ensure_rls(request, db)

    # Resolve tenant_id from claims/session
    tid = rls_core.tenant_id_from_request(request)
    if not tid:
        # Preserve previous behaviour: require tenant context
        raise HTTPException(status_code=403, detail="missing_tenant")
    return tid


def get_current_tenant_id(request: Request, db: Session = Depends(get_db)) -> str:
    """FastAPI dependency that returns the current tenant UUID, ensuring RLS.

    Provided for backward compatibility with routers importing from
    `app.middleware.rls`.
    """
    return ensure_rls(request, db)


__all__ = ["ensure_rls", "get_current_tenant_id"]
