"""
Tenant middleware/dependencies for routers.

Provides ensure_tenant and get_current_user for routers to access
auth + RLS stack. 100% UUID - no legacy int conversions.
"""

from __future__ import annotations

import logging
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import set_tenant_guc

logger = logging.getLogger(__name__)


def _validate_tenant_uuid(claim_tid: str | None) -> str:
    """
    Validates tenant_id from claims is a valid UUID string.
    Raises HTTPException if missing or invalid.
    """
    if not claim_tid:
        raise HTTPException(status_code=403, detail="missing_tenant")

    tenant_uuid = str(claim_tid).strip()

    # Validación básica de formato UUID
    if len(tenant_uuid) != 36 or tenant_uuid.count("-") != 4:
        raise HTTPException(
            status_code=403,
            detail=f"invalid_tenant_format: expected UUID, got {tenant_uuid}",
        )

    return tenant_uuid


def ensure_tenant(request: Request, db: Session = Depends(get_db)) -> str:
    """FastAPI dependency that ensures a valid tenant and sets the DB GUC.

    - Parses/validates the access token via with_access_claims
    - Validates tenant_id is UUID format
    - Sets `app.tenant_id` (SET LOCAL) for RLS/trigger coherence
    - Returns the tenant UUID string

    DEV MODE: Si no hay token válido, usa el primer tenant de la BD
    """
    import os

    dev_mode = os.getenv("ENVIRONMENT", "production") != "production"
    logger.info(f"ensure_tenant: dev_mode={dev_mode}, env={os.getenv('ENVIRONMENT')}")

    try:
        claims = with_access_claims(request)
        claim_tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        tenant_uuid = _validate_tenant_uuid(
            str(claim_tid) if claim_tid is not None else None
        )
        logger.info(f"Token validated: tenant_uuid={tenant_uuid}")
    except (HTTPException, Exception) as e:
        # FALLBACK para desarrollo: usar primer tenant de la BD
        logger.warning(f"Auth failed: {e}, dev_mode={dev_mode}")
        if dev_mode:
            from sqlalchemy import text

            result = db.execute(
                text("SELECT id FROM tenants ORDER BY created_at LIMIT 1")
            ).fetchone()
            if result:
                tenant_uuid = str(result[0])
                logger.info(f"✅ DEV MODE: Using fallback tenant_id={tenant_uuid}")
            else:
                raise HTTPException(status_code=403, detail="no_tenants_found")
        else:
            raise

    try:
        set_tenant_guc(db, tenant_uuid, persist=False)
        print(f"[DEBUG] RLS set for tenant: {tenant_uuid}")
    except Exception as e:
        # Non-fatal: proceed without aborting request
        print(f"[ERROR] Failed to set RLS for tenant {tenant_uuid}: {e}")
        pass
    # Also expose on request for downstream use
    try:
        request.state.tenant_id = tenant_uuid
    except Exception:
        pass
    return tenant_uuid


def get_current_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Returns user dict from access claims for routers.

    Expected keys: id, user_id, tenant_id (UUID), roles
    All values are from JWT claims - 100% UUID, no conversions.
    """
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        claims = with_access_claims(request)

    uid = claims.get("user_id") if isinstance(claims, dict) else None
    if uid is None:
        raise HTTPException(status_code=401, detail="missing_user")

    # Validate tenant_id from claims (must be UUID)
    claim_tid = claims.get("tenant_id") if isinstance(claims, dict) else None
    tenant_uuid = _validate_tenant_uuid(
        str(claim_tid) if claim_tid is not None else None
    )

    return {
        "id": uid,
        "user_id": uid,
        "tenant_id": tenant_uuid,
        "roles": claims.get("roles", []) if isinstance(claims, dict) else [],
    }
