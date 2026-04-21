"""Core dependencies for FastAPI dependency injection."""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db as _get_db
from app.core.access_guard import with_access_claims


def get_db(request: Request) -> Iterator[Session]:
    """Get database session dependency."""
    yield from _get_db(request)


def get_tenant_uuid(request: Request) -> UUID:
    """
    Extract tenant_id UUID from JWT claims already set by auth middleware.

    Use this as a plain call inside sync route handlers:
        tenant_id = get_tenant_uuid(request)

    Raises HTTPException(401) if claims are missing or tenant_id is invalid.
    """
    claims = getattr(request.state, "access_claims", None) or {}
    raw = claims.get("tenant_id") if isinstance(claims, dict) else None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="tenant_id inválido")


async def get_tenant_id_from_token(request: Request) -> UUID:
    """
    Extract tenant_id from JWT token in request.

    Raises HTTPException(401) if token is invalid or missing tenant_id.
    """
    claims: dict[str, Any] = with_access_claims(request)

    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant_id in token")

    # Convert to UUID if it's a string
    if isinstance(tenant_id, str):
        try:
            return UUID(tenant_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid tenant_id format")

    return tenant_id


def get_current_tenant_id(request: Request) -> UUID:
    """
    Centralizada: Extrae tenant_id desde request claims con fallback para dev mode.

    Comportamiento:
    1. Intenta obtener desde request.state.tenant_id (set por middleware)
    2. Sino, busca en access_claims.tenant_id
    3. En dev mode, fallback a primer tenant de BD si no hay token
    4. Siempre retorna UUID válido o lanza HTTPException

    Uso como dependency:
        tenant_id: UUID = Depends(get_current_tenant_id)
    """
    import logging
    import os

    from sqlalchemy import text

    from app.config.database import SessionLocal

    logger = logging.getLogger(__name__)

    # 1. Intentar desde state directo (middleware)
    tid = getattr(request.state, "tenant_id", None)
    if tid is not None:
        return UUID(str(tid))

    # 2. Intentar desde access_claims
    claims = getattr(request.state, "access_claims", None) or {}
    if isinstance(claims, dict):
        tid = claims.get("tenant_id") or claims.get("empresa_id")
        if tid is not None:
            return UUID(str(tid))

    # 3. Dev mode fallback - solo si no es producción
    dev_mode = os.getenv("ENVIRONMENT", "production") != "production"
    if dev_mode:
        try:
            with SessionLocal() as db_temp:
                rows = db_temp.execute(
                    text("SELECT id FROM tenants ORDER BY created_at LIMIT 1")
                ).fetchall()
                if len(rows) == 1:
                    logger.warning("DEV MODE: Using fallback tenant")
                    return UUID(str(rows[0][0]))
        except Exception as e:
            logger.error(f"DEV MODE fallback failed: {e}")

    # 4. Si no hay tenant_id válido, lanzar error
    raise HTTPException(status_code=401, detail="tenant_id_required")


def get_current_tenant_id_str(request: Request) -> str:
    """
    Versión string de get_current_tenant_id para compatibilidad con código existente.
    """
    return str(get_current_tenant_id(request))
