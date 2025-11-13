from fastapi.testclient import TestClient
import pytest


@pytest.mark.xfail(reason="CSRF enforced in tests without HTTPS; CRUD blocked (403)")
def test_admin_empresas_crud(client: TestClient, db, superuser_factory, admin_login):
    tok = admin_login()

    # ensure CSRF cookie and get token
    csrf = client.get("/api/v1/admin/auth/csrf").json().get("csrfToken")
    # create
    r = client.post(
        "/api/v1/admin/empresas/completa-json",
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
    r = client.get(
        "/api/v1/admin/empresas/completa-json",
        headers={"Authorization": f"Bearer {tok}"},
    )
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
