from fastapi.testclient import TestClient
from app.models import Empresa


def _admin_token(client: TestClient, superuser_factory) -> str:
    superuser_factory(email="root@admin.com", username="root", password="secret")
    r = client.post("/api/v1/admin/auth/login", json={"identificador": "root", "password": "secret"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_admin_empresas_list_empty(client: TestClient, superuser_factory):
    tok = _admin_token(client, superuser_factory)
    r = client.get("/api/v1/admin/empresas", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert r.json() == []


def test_admin_empresas_list_with_data(client: TestClient, db, superuser_factory):
    tok = _admin_token(client, superuser_factory)
    e1 = Empresa(nombre="Empresa Uno")
    e2 = Empresa(nombre="Empresa Dos")
    db.add_all([e1, e2])
    db.commit()

    r = client.get("/api/v1/admin/empresas", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = {item["nombre"] for item in data}
    assert {"Empresa Uno", "Empresa Dos"}.issubset(names)
