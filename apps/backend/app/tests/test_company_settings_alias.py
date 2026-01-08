from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant


def test_company_settings_endpoint_creates_row(client: TestClient, db):
    # Ensure clean slate
    db.query(CompanySettings).delete()
    db.query(Tenant).delete()
    db.commit()

    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    db.add(tenant)
    db.commit()

    settings = CompanySettings(
        tenant_id=tenant.id,
        default_language="es",
        timezone="Europe/Madrid",
        currency="EUR",
        primary_color="#000000",
        secondary_color="#ffffff",
    )
    db.add(settings)
    db.commit()

    r = client.get("/api/v1/company/settings")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("currency") == "EUR"
