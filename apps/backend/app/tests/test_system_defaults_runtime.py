import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant
from app.services.system_defaults_service import update_system_default


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
