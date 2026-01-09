from uuid import uuid4
import os

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant


def test_company_settings_endpoint_creates_row(client: TestClient, db):
    # Ensure clean slate
    try:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("TRUNCATE chart_of_accounts CASCADE"))
            db.execute(text("TRUNCATE import_batches CASCADE"))
        else:
            db.execute(text("DELETE FROM chart_of_accounts"))
            db.execute(text("DELETE FROM import_batches"))
        db.commit()
    except Exception:
        db.rollback()

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

    previous_tid = os.environ.get("TEST_TENANT_ID")
    os.environ["TEST_TENANT_ID"] = str(tenant.id)
    try:
        r = client.get("/api/v1/company/settings")
    finally:
        if previous_tid is None:
            os.environ.pop("TEST_TENANT_ID", None)
        else:
            os.environ["TEST_TENANT_ID"] = previous_tid
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("currency") == "EUR"
