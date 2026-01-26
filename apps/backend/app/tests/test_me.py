import secrets

from fastapi.testclient import TestClient


def test_me_admin_requires_bearer(client: TestClient):
    r = client.get("/api/v1/me/admin")
    assert r.status_code in (401, 403)


def test_me_admin_ok(client: TestClient, db, superuser_factory):
    test_password = secrets.token_urlsafe(12)  # Random password for testing
    su = superuser_factory(email="root@admin.com", username="root", password=test_password)  # noqa: F841
    # Login admin
    r = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "root", "password": test_password},
    )
    assert r.status_code == 200
    tok = r.json()["access_token"]

    # Llama /me/admin con Bearer
    r2 = client.get("/api/v1/me/admin", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("user_id") is not None
    assert data.get("user_type") in ("admin", "superadmin")


def test_me_tenant_ok(client: TestClient, db, usuario_empresa_factory):
    test_password = secrets.token_urlsafe(12)  # Random password for testing
    u = usuario_empresa_factory(email="t@x.com", username="tenant", password=test_password)  # noqa: F841

    # Login tenant
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "tenant", "password": test_password},
    )
    assert r.status_code == 200
    tok = r.json()["access_token"]

    # Llama /me/tenant con Bearer
    r2 = client.get("/api/v1/me/tenant", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("user_id") is not None
    assert data.get("tenant_id") is not None


def test_admin_refresh_rotation(client: TestClient, db, superuser_factory):
    test_password = secrets.token_urlsafe(12)  # Random password for testing
    superuser_factory(email="admin@x.com", username="admin", password=test_password)
    r = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "admin", "password": test_password},
    )
    assert r.status_code == 200
    old_rt = r.cookies.get("refresh_token")
    assert old_rt
    r2 = client.post(
        "/api/v1/admin/auth/refresh",
        headers={"Cookie": f"refresh_token={old_rt}"},
    )
    assert r2.status_code == 200
    new_rt = r2.cookies.get("refresh_token")
    assert new_rt and new_rt != old_rt
