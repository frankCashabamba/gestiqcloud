import pytest

from app.platform.http.router import build_api_router

pytestmark = pytest.mark.no_db


def test_build_api_router_mounts_tenant_billing_routes():
    router = build_api_router()
    paths = {getattr(route, "path", "") for route in router.routes}

    assert "/tenant/billing/plans" in paths
    assert "/tenant/billing/subscription" in paths
    assert "/tenant/billing/subscribe" in paths
    assert "/tenant/billing/change-plan" in paths
    assert "/tenant/billing/cancel" in paths
    assert "/tenant/billing/portal" in paths
    assert "/tenant/billing/webhook/stripe" in paths
    assert "/admin/companies/{tenant_id}/billing/plans" in paths
    assert "/admin/companies/{tenant_id}/billing/subscription" in paths
    assert "/admin/companies/{tenant_id}/billing/subscribe" in paths
    assert "/admin/companies/{tenant_id}/billing/change-plan" in paths
    assert "/admin/companies/{tenant_id}/billing/cancel" in paths
    assert "/admin/companies/{tenant_id}/billing/portal" in paths
    assert "/admin/companies/{tenant_id}/feature-flags" in paths
