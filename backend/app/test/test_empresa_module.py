from fastapi.testclient import TestClient
import pytest


def _admin_login(client: TestClient, superuser_factory):
    su = superuser_factory(email="root@admin.com", username="root", password="secret")
    r = client.post("/api/v1/admin/auth/login", json={"identificador": "root", "password": "secret"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.mark.xfail(reason="CSRF enforced in tests without HTTPS; CRUD blocked (403)")
def test_admin_empresas_crud(client: TestClient, db, superuser_factory):
    tok = _admin_login(client, superuser_factory)

    # ensure CSRF cookie and get token
    csrf = client.get("/api/v1/admin/auth/csrf").json().get("csrfToken")
    # create
    r = client.post(
        "/api/v1/admin/empresas/",
        headers={
            "Authorization": f"Bearer {tok}",
            "X-CSRF-Token": csrf or client.cookies.get("csrf_token", ""),
        },
        json={"nombre": "Acme SA", "slug": "acme"},
    )
    assert r.status_code == 200
    emp = r.json()
    emp_id = emp["id"]

    # list
    r = client.get("/api/v1/admin/empresas/", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert any(e["id"] == emp_id for e in r.json())

    # update
    r = client.put(
        f"/api/v1/admin/empresas/{emp_id}",
        headers={
            "Authorization": f"Bearer {tok}",
            "X-CSRF-Token": csrf or client.cookies.get("csrf_token", ""),
        },
        json={"nombre": "Acme Corp"},
    )
    assert r.status_code == 200
    assert r.json()["nombre"] == "Acme Corp"

    # delete
    r = client.delete(
        f"/api/v1/admin/empresas/{emp_id}",
        headers={
            "Authorization": f"Bearer {tok}",
            "X-CSRF-Token": csrf or client.cookies.get("csrf_token", ""),
        },
    )
    assert r.status_code == 200
