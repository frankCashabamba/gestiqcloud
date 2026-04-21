"""
Unified authentication dependencies for FastAPI routers.

Consolidates authentication logic from multiple sources:
- app/middleware/tenant.py (get_current_user)
- app/core/access_guard.py (get_current_user_context)
- app/modules/identity/interface/http/protected.py

Provides single source of truth for auth dependencies.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.core.access_guard import with_access_claims

logger = logging.getLogger(__name__)


def _validate_tenant_uuid(claim_tid: str | None) -> str:
    """
    Validates tenant_id from claims is a valid UUID string.
    Raises HTTPException if missing or invalid.
    """
    if not claim_tid:
        raise HTTPException(status_code=403, detail="missing_tenant")

    tenant_uuid = str(claim_tid).strip()
    try:
        return str(UUID(tenant_uuid))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=403,
            detail=f"invalid_tenant_format: expected UUID, got {tenant_uuid}",
        )


class AuthManager:
    """Centralized authentication management."""

    @staticmethod
    def get_current_user(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
        """
        Returns user dict from access claims for routers.

        Expected keys: id, user_id, tenant_id (UUID), roles
        All values are from JWT claims - 100% UUID, no conversions.

        This replaces the duplicate implementations in:
        - app/middleware/tenant.py
        - app/core/access_guard.py
        """
        claims = getattr(request.state, "access_claims", None)
        if not isinstance(claims, dict):
            claims = with_access_claims(request)

        uid = claims.get("user_id") if isinstance(claims, dict) else None
        if uid is None:
            raise HTTPException(status_code=401, detail="missing_user")

        # Validate tenant_id from claims (must be UUID)
        claim_tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        tenant_uuid = _validate_tenant_uuid(str(claim_tid) if claim_tid is not None else None)

        return {
            "id": uid,
            "user_id": uid,
            "tenant_id": tenant_uuid,
            "roles": claims.get("roles", []) if isinstance(claims, dict) else [],
        }

    @staticmethod
    async def get_current_user_context(request: Request) -> dict[str, Any]:
        """
        Async version of get_current_user for contexts that don't need DB.

        This replaces get_current_user_context from app/core/access_guard.py
        """
        return with_access_claims(request)

    @staticmethod
    def ensure_tenant(request: Request, db: Session = Depends(get_db)) -> str:
        """
        FastAPI dependency that ensures a valid tenant and sets the DB GUC.

        - Parses/validates the access token via with_access_claims
        - Validates tenant_id is UUID format
        - Sets `app.tenant_id` (SET LOCAL) for RLS/trigger coherence
        - Returns the tenant UUID string

        DEV MODE: Si no hay token válido, usa el primer tenant de la BD

        This replaces ensure_tenant from app/middleware/tenant.py
        """
        from sqlalchemy import text

        from app.db.rls import set_tenant_guc

        dev_mode = settings.ENVIRONMENT in ("development", "local")
        logger.debug(f"ensure_tenant: dev_mode={dev_mode}, env={settings.ENVIRONMENT}")

        try:
            claims = with_access_claims(request)
            claim_tid = claims.get("tenant_id") if isinstance(claims, dict) else None
            tenant_uuid = _validate_tenant_uuid(str(claim_tid) if claim_tid is not None else None)
            logger.debug(f"Token validated: tenant_uuid={tenant_uuid}")
        except (HTTPException, Exception) as e:
            # FALLBACK para desarrollo: usar primer tenant de la BD
            logger.warning(f"Auth failed: {e}, dev_mode={dev_mode}")
            if dev_mode:
                result = db.execute(
                    text("SELECT id FROM tenants ORDER BY created_at LIMIT 1")
                ).fetchone()
                if result:
                    tenant_uuid = str(result[0])
                    logger.debug(f"DEV MODE: Using fallback tenant_id={tenant_uuid}")
                else:
                    raise HTTPException(status_code=403, detail="no_tenants_found")
            else:
                raise

        try:
            set_tenant_guc(db, tenant_uuid, persist=False)
            logger.debug("RLS set for tenant %s", tenant_uuid)
        except Exception:
            # Non-fatal: proceed without aborting request
            logger.exception("Failed to set RLS for tenant %s", tenant_uuid)

        # Also expose on request for downstream use
        try:
            request.state.tenant_id = tenant_uuid
        except Exception:
            pass
        return tenant_uuid


# Export the main dependencies for backward compatibility
get_current_user = AuthManager.get_current_user
get_current_user_context = AuthManager.get_current_user_context
ensure_tenant = AuthManager.ensure_tenant
