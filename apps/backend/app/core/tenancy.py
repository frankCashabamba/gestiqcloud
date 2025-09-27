"""Tenancy helpers.

Provides a stable import path for RLS/tenant resolution.
"""

try:
    from app.db.rls import (  # noqa: F401
        tenant_from_request,
        get_current_tenant,
    )
except Exception:  # pragma: no cover
    pass

try:
    from app.middleware.tenant_middleware import tenant_context_middleware  # noqa: F401
except Exception:  # pragma: no cover
    pass

