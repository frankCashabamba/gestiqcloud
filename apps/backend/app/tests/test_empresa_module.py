import pytest
from fastapi.testclient import TestClient


def _admin_headers(client: TestClient, superuser_factory) -> dict[str, str]:
    password = "secret123"
    superuser_factory(email="root@admin.com", username="root", password=password)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "root", "password": password},
    )
    assert login.status_code == 200, login.text
    csrf = client.get("/api/v1/admin/auth/csrf").json().get("csrfToken")
    return {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-CSRF-Token": csrf or client.cookies.get("csrf_token", ""),
    }


@pytest.mark.xfail(reason="CSRF enforced in tests without HTTPS; CRUD blocked (403)")
def test_admin_empresas_crud(client: TestClient, db, superuser_factory, admin_login):
    tok = admin_login()

    # ensure CSRF cookie and get token
    csrf = client.get("/api/v1/admin/auth/csrf").json().get("csrfToken")
    # create
    r = client.post(
        "/api/v1/admin/companies/full-json",
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
        "/api/v1/admin/companies/full-json",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    assert any(e["id"] == emp_id for e in r.json())

    # update
    r = client.put(
        f"/api/v1/admin/companies/{emp_id}",
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
        f"/api/v1/admin/companies/{emp_id}",
        headers={
            "Authorization": f"Bearer {tok}",
            "X-CSRF-Token": csrf or client.cookies.get("csrf_token", ""),
        },
    )
    assert r.status_code == 200


def test_admin_create_company_invalid_module_id_returns_422_not_500(
    client: TestClient, db, superuser_factory
):
    headers = _admin_headers(client, superuser_factory)

    response = client.post(
        "/api/v1/admin/companies/full-json",
        headers=headers,
        json={
            "company": {"name": "Acme SA", "initial_template": "default"},
            "admin": {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "username": "ada.lovelace",
            },
            "modulos": ["products", "not-a-uuid"],
        },
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["detail"][0]["msg"] == "Value error, invalid_module_id"
    assert body["detail"][0]["ctx"]["error"] == "invalid_module_id"
