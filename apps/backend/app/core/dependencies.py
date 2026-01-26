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
