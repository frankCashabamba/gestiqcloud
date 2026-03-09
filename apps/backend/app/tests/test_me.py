import secrets
from collections import Counter

from fastapi.testclient import TestClient


def test_me_admin_requires_bearer(client: TestClient):
    r = client.get("/api/v1/me/admin")
    assert r.status_code in (401, 403)


def test_me_admin_ok(client: TestClient, db, superuser_factory):
    test_password = secrets.token_urlsafe(12)  # Random password for testing
    superuser_factory(email="root@admin.com", username="root", password=test_password)
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
    usuario_empresa_factory(email="t@x.com", username="tenant", password=test_password)

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


def test_me_tenant_marks_legacy_onboarding_as_complete(client: TestClient, db, usuario_empresa_factory):
    from app.models.company.company_settings import CompanySettings

    test_password = secrets.token_urlsafe(12)
    _, tenant = usuario_empresa_factory(
        empresa_nombre="Default",
        empresa_slug="default",
        email="legacy@x.com",
        username="legacy",
        password=test_password,
    )
    tenant.name = "Default"
    tenant.slug = "default"
    db.add(
        CompanySettings(
            tenant_id=tenant.id,
            default_language="es",
            timezone="Europe/Madrid",
            currency="EUR",
            primary_color="#2563eb",
            secondary_color="#ffffff",
            settings={},
        )
    )
    db.commit()

    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "legacy", "password": test_password},
    )
    assert r.status_code == 200
    tok = r.json()["access_token"]

    r2 = client.get("/api/v1/me/tenant", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    assert r2.json()["onboarding_complete"] is True


def test_critical_routes_are_not_duplicated(client: TestClient):
    counts = Counter()
    for route in client.app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if not path:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            counts[(method, path)] += 1

    critical = [
        ("GET", "/api/v1/me/tenant"),
        ("GET", "/api/v1/me/admin"),
        ("POST", "/api/v1/tenant/auth/login"),
        ("POST", "/api/v1/tenant/auth/refresh"),
        ("POST", "/api/v1/tenant/auth/logout"),
        ("GET", "/api/v1/modules"),
        ("GET", "/api/v1/admin/modules"),
        ("GET", "/api/v1/sectors/{code}/config"),
        ("GET", "/api/v1/dashboard/kpis"),
        ("POST", "/api/v1/tenant/sales_orders/{order_id}/invoice"),
        ("GET", "/api/v1/tenant/pos/shifts/{shift_id}/summary"),
    ]
    for key in critical:
        assert counts[key] == 1, f"Duplicated route detected: {key} -> {counts[key]}"


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
