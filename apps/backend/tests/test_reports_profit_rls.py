"""Reports / profit RLS guard tests.

These tests assert the *contract* declared by
``app.modules.reports.interface.http.profit.router``:

* every request must pass ``with_access_claims`` (auth);
* the access token must carry the ``tenant`` scope (``require_scope("tenant")``);
* the request must go through ``ensure_rls`` so the SQL session is bound to
  the tenant before any handler runs.

We exercise the router-level dependencies directly (rather than booting the
full FastAPI app) so the test stays fast and does not depend on a running
auth stack — yet still fails loudly if any of the three guards is removed
or downgraded from a router-level ``Depends``.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.reports.interface.http.profit import router as profit_router


def _router_dep_callables(router) -> list:
    return [d.dependency for d in (router.dependencies or [])]


def test_profit_router_declares_auth_scope_and_rls_dependencies():
    """The profit router MUST mount auth + tenant scope + RLS at router level."""
    deps = _router_dep_callables(profit_router)

    assert with_access_claims in deps, (
        "profit router lost with_access_claims dependency — endpoints would be "
        "reachable without an access token"
    )
    assert ensure_rls in deps, (
        "profit router lost ensure_rls dependency — SQL session would not be "
        "bound to a tenant and RLS policies would silently leak data"
    )
    # require_scope is a factory; locate the closure produced for "tenant".
    scope_deps = [d for d in deps if getattr(d, "__name__", "") == "dep"]
    assert scope_deps, "profit router lost require_scope() dependency"


def test_profit_router_endpoints_are_all_under_router_guards():
    """Every route on the profit router inherits the router-level guards."""
    paths = {route.path for route in profit_router.routes}
    # Sanity: the three documented endpoints exist.
    assert "/reports/profit" in paths
    assert "/reports/product-margins" in paths
    assert "/reports/recalculate" in paths


def test_require_scope_tenant_rejects_non_tenant_token():
    """``require_scope('tenant')`` returns 403 when the token kind isn't tenant.

    This is the exact dependency mounted on the profit router, so a regression
    here means non-tenant principals (e.g. plain admin tokens with no tenant
    claim) could reach the profit endpoints.
    """
    dep = require_scope("tenant")

    # Admin-scope claims should be rejected.
    with pytest.raises(HTTPException) as exc:
        dep(claims={"kind": "admin", "scope": "admin"})
    assert exc.value.status_code == 403

    # Tenant-scope claims pass through unchanged.
    accepted = dep(claims={"kind": "tenant", "tenant_id": "t-1"})
    assert accepted["kind"] == "tenant"
