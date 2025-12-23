from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.company.company_settings import CompanySettings
from app.models.core.settings import TenantSettings
from app.models.tenant import Tenant


def test_tenantsettings_alias_writes_company_settings(db):
    tid = uuid4()
    ts = TenantSettings(tenant_id=tid, default_language="fr", timezone="Europe/Paris", currency="EUR")
    db.add(ts)
    db.commit()

    stored = db.query(CompanySettings).filter(CompanySettings.tenant_id == tid).first()
    assert stored is not None
    assert stored.default_language == "fr"
    assert stored.timezone == "Europe/Paris"
    assert stored.currency == "EUR"


def test_company_settings_endpoint_creates_row(client: TestClient, db):
    # Ensure clean slate
    db.query(CompanySettings).delete()
    db.query(Tenant).delete()
    db.commit()

    tenant = Tenant(id=uuid4(), name="Acme", slug="acme")
    db.add(tenant)
    db.commit()

    r = client.get("/api/v1/company/settings")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("currency") == "EUR"  # model default

    stored = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant.id).first()
    assert stored is not None
