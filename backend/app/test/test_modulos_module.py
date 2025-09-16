from fastapi.testclient import TestClient
import pytest


def _admin_login(client: TestClient, superuser_factory):
    su = superuser_factory(email="root@admin.com", username="root", password="secret")
    r = client.post("/api/v1/admin/auth/login", json={"identificador": "root", "password": "secret"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.mark.xfail(reason="Admin modulos router not mounted in this minimal test env")
def test_admin_modulos_list(client: TestClient, db, superuser_factory):
    tok = _admin_login(client, superuser_factory)
    # ping route to assert router is mounted and auth works
    rp = client.get("/api/v1/admin/modulos/ping", headers={"Authorization": f"Bearer {tok}"})
    assert rp.status_code == 200
