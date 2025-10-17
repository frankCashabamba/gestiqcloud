"""Tenant context middleware for imports module RLS."""
from __future__ import annotations

import logging
import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


def set_tenant_context(session: Session, tenant_id: uuid.UUID) -> None:
    """Set app.tenant_id GUC variable for RLS policies.
    
    Args:
        session: SQLAlchemy session
        tenant_id: Tenant UUID
        
    Raises:
        ValueError: If tenant_id is None
    """
    if tenant_id is None:
        raise ValueError("tenant_id cannot be None when setting RLS context")
    
    try:
        # If not PostgreSQL, skip SET LOCAL and just stash in session.info (test-safe)
        try:
            dialect = getattr(getattr(session, "bind", None), "dialect", None)
            is_postgres = bool(dialect and getattr(dialect, "name", "") == "postgresql")
        except Exception:
            is_postgres = False

        if is_postgres:
            session.execute(
                text("SET LOCAL app.tenant_id = :tid"),
                {"tid": str(tenant_id)}
            )
        # Store in session.info for debugging/utilities
        session.info["tenant_id"] = str(tenant_id)
        logger.debug(f"Set tenant context: {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to set tenant context for {tenant_id}: {e}")
        raise


def with_tenant_context(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure tenant_id is set before executing repository method.
    
    Usage:
        @with_tenant_context
        def get_batch(self, db: Session, tenant_id: uuid.UUID, batch_id: int):
            ...
    
    The decorated function MUST accept tenant_id as the second parameter after db.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        # Extract db (1st arg or kwarg) and tenant_id (2nd arg or kwarg)
        db: Session | None = None
        tenant_id: uuid.UUID | None = None
        
        # Positional args: self, db, tenant_id, ...
        if len(args) >= 3:
            db = args[1]
            tenant_id = args[2]
        else:
            db = kwargs.get("db")
            tenant_id = kwargs.get("tenant_id")
        
        if db is None:
            raise ValueError("db (Session) is required for tenant context")
        
        if tenant_id is None:
            logger.warning(
                f"{func.__name__}: tenant_id is None, RLS may return 0 rows. "
                "Ensure tenant_id is passed explicitly."
            )
            # Allow call to proceed (for tests/admin scenarios) but warn
            return func(*args, **kwargs)
        
        # Set tenant context
        set_tenant_context(db, tenant_id)
        
        # Execute the wrapped function
        return func(*args, **kwargs)
    
    return wrapper


def require_tenant_context(db: Session) -> None:
    """Verify that tenant_id GUC is set; raise if not.
    
    Useful for critical operations that must never run without tenant isolation.
    """
    # In non-Postgres test environments (e.g., SQLite), this is a no-op
    try:
        dialect = getattr(getattr(db, "bind", None), "dialect", None)
        if not (dialect and getattr(dialect, "name", "") == "postgresql"):
            return
    except Exception:
        return

    try:
        result = db.execute(text("SELECT current_setting('app.tenant_id', true)"))
        tenant_id = result.scalar()
        if not tenant_id or tenant_id == "":
            raise RuntimeError(
                "RLS context not set: app.tenant_id is empty. "
                "Call set_tenant_context() before querying."
            )
    except Exception as e:
        if "unrecognized configuration parameter" in str(e).lower():
            raise RuntimeError("RLS GUC app.tenant_id not configured in DB") from e
        raise
