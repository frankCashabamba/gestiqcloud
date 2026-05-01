"""Routing tests for analytics dashboard KPIs.

Covers:
- Canonical mount at /api/v1/tenant/dashboard/kpis (scope=tenant + RLS).
- Legacy alias /api/v1/dashboard/kpis still reachable, but returns the
  X-Deprecated response header pointing to the canonical URL.

The test relies on the pytest bypass in `app.core.access_guard.with_access_claims`,
which injects permissive tenant-scoped claims under PYTEST_CURRENT_TEST so the
`require_scope("tenant")` and `ensure_rls` dependencies are satisfied without
needing a real JWT.
"""

from __future__ import annotations

import pytest

CANONICAL_PATH = "/api/v1/tenant/dashboard/kpis"
LEGACY_PATH = "/api/v1/dashboard/kpis"


def _has_route(app, path: str) -> bool:
    return any(getattr(r, "path", None) == path for r in app.routes)


def test_analytics_router_mounted_at_tenant_prefix(client):
    """The analytics router must be mounted under /api/v1/tenant."""
    app = client.app
    assert _has_route(app, CANONICAL_PATH), (
        f"Expected canonical route {CANONICAL_PATH} to be registered"
    )


def test_analytics_legacy_alias_still_mounted(client):
    """Legacy /api/v1/dashboard/kpis must remain mounted for 1 release."""
    app = client.app
    assert _has_route(app, LEGACY_PATH), (
        f"Expected legacy alias {LEGACY_PATH} to be registered for backward "
        "compatibility"
    )


def test_canonical_endpoint_returns_200_with_tenant_scope(client, db):
    """GET /api/v1/tenant/dashboard/kpis should respond 200 with tenant claims."""
    resp = client.get(CANONICAL_PATH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, dict)


def test_legacy_endpoint_emits_deprecation_header(client, db):
    """Legacy path responds 200 and includes `X-Deprecated` pointing to /tenant/."""
    resp = client.get(LEGACY_PATH)
    assert resp.status_code == 200, resp.text
    deprecated = resp.headers.get("X-Deprecated") or resp.headers.get("x-deprecated")
    assert deprecated is not None, "Legacy endpoint must emit X-Deprecated header"
    assert "tenant/dashboard/kpis" in deprecated


def test_canonical_endpoint_does_not_emit_deprecation_header(client, db):
    """The canonical endpoint must NOT carry the deprecation header."""
    resp = client.get(CANONICAL_PATH)
    assert resp.status_code == 200
    assert "X-Deprecated" not in resp.headers
    assert "x-deprecated" not in resp.headers


@pytest.mark.parametrize("path", [CANONICAL_PATH, LEGACY_PATH])
def test_endpoints_accept_sector_query_param(client, db, path):
    resp = client.get(path, params={"sector": "default"})
    assert resp.status_code == 200, resp.text
