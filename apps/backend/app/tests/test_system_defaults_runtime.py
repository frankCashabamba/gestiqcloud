import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt_provider import get_token_service
from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant
from app.services.system_defaults_service import update_system_default


def _tenant_headers(tenant: Tenant, slug: str) -> dict[str, str]:
    token = get_token_service().issue_access(
        {
            "user_id": str(uuid4()),
            "tenant_id": str(tenant.id),
            "empresa_slug": slug,
            "scope": "tenant",
            "kind": "tenant",
            "sub": "tenant@example.com",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_theme_endpoint_uses_system_defaults(client: TestClient, db):
    update_system_default(db, "theme.colors.primary", "#123456")
    update_system_default(db, "theme.typography.font_family", "DM Sans, sans-serif")
    update_system_default(db, "theme.radius.md", "14px")

    response = client.get("/api/v1/company/settings/theme")

    assert response.status_code == 200
    body = response.json()
    assert body["colors"]["primary"] == "#123456"
    assert body["typography"]["fontFamily"] == "DM Sans, sans-serif"
    assert body["radius"]["md"] == "14px"


def test_theme_endpoint_preserves_company_colors_over_global_defaults(client: TestClient, db):
    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    db.add(tenant)
    db.flush()
    db.add(
        CompanySettings(
            tenant_id=tenant.id,
            default_language="es",
            timezone="Europe/Madrid",
            currency="EUR",
            primary_color="#999999",
            secondary_color="#222222",
        )
    )
    db.commit()

    update_system_default(db, "theme.colors.primary", "#123456")
    update_system_default(db, "theme.colors.success", "#00ff00")

    response = client.get("/api/v1/company/settings/theme?empresa=acme")

    assert response.status_code == 200
    body = response.json()
    assert body["colors"]["primary"] == "#999999"
    assert body["colors"]["secondary"] == "#222222"
    assert body["colors"]["success"] == "#00ff00"


def test_theme_endpoint_prioritizes_authenticated_tenant_over_empresa_query(client: TestClient, db):
    slug_a = f"pan-{uuid4().hex[:8]}"
    slug_b = f"taller-{uuid4().hex[:8]}"
    tenant_a = Tenant(
        id=uuid4(), name="Panaderia Demo", slug=slug_a, sector_template_name="panaderia"
    )
    tenant_b = Tenant(id=uuid4(), name="Taller Demo", slug=slug_b, sector_template_name="taller")
    db.add_all([tenant_a, tenant_b])
    db.flush()
    db.add(
        CompanySettings(
            tenant_id=tenant_b.id,
            default_language="es",
            timezone="Europe/Madrid",
            currency="EUR",
            primary_color="#111111",
            secondary_color="#333333",
        )
    )
    db.commit()

    response = client.get(
        f"/api/v1/company/settings/theme?empresa={slug_a}",
        headers=_tenant_headers(tenant_b, slug_b),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["brand"]["name"] == "Taller Demo"
    assert body["sector"] == "taller"
    assert body["colors"]["primary"] == "#111111"


def test_company_limits_endpoint_uses_system_defaults(client: TestClient, db):
    tenant = Tenant(id=uuid4(), name="Limits", slug="limits")
    db.add(tenant)
    db.commit()

    update_system_default(db, "company.user_limit_default", "42")
    update_system_default(db, "company.allow_custom_roles_default", "false")

    previous_tid = os.environ.get("TEST_TENANT_ID")
    os.environ["TEST_TENANT_ID"] = str(tenant.id)
    try:
        response = client.get("/api/v1/company/settings/limits")
    finally:
        if previous_tid is None:
            os.environ.pop("TEST_TENANT_ID", None)
        else:
            os.environ["TEST_TENANT_ID"] = previous_tid

    assert response.status_code == 200
    assert response.json() == {"user_limit": 42, "allow_custom_roles": False}
