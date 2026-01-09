from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.models.tenant import Tenant


def _admin_token(client: TestClient, superuser_factory) -> str:
    superuser_factory(email="root@admin.com", username="root", password="secret")
    r = client.post(
        "/api/v1/admin/auth/login", json={"identificador": "root", "password": "secret"}
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def test_admin_empresas_list_empty(client: TestClient, db, superuser_factory):
    # Clean any existing tenants first
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

    db.query(Tenant).delete()
    db.commit()

    tok = _admin_token(client, superuser_factory)
    r = client.get("/api/v1/admin/empresas", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert r.json() == []


def test_admin_empresas_list_with_data(client: TestClient, db, superuser_factory):
    tok = _admin_token(client, superuser_factory)
    # Tenant is now the primary entity (replaces Empresa)
    t1 = Tenant(id=uuid4(), name="Empresa Uno", slug="empresa-uno")
    t2 = Tenant(id=uuid4(), name="Empresa Dos", slug="empresa-dos")
    db.add_all([t1, t2])
    db.commit()

    r = client.get("/api/v1/admin/empresas", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = {item["name"] for item in data}
    assert {"Empresa Uno", "Empresa Dos"}.issubset(names)
