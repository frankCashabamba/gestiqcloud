def test_admin_login_ok(client, db, superuser_factory):
    su = superuser_factory(email="root@x.com", username="root", password="secret")  # noqa: F841
    r = client.post(
        "/api/v1/auth/login",
        json={"identificador": "ROOT", "password": "secret"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.cookies


def test_tenant_login_and_refresh(client, db, usuario_empresa_factory):
    u = usuario_empresa_factory(email="a@x.com", username="a", password="secret")  # noqa: F841
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "A", "password": "secret"},
    )
    assert r.status_code == 200

    # Usa las cookies que mantiene el cliente entre peticiones
    rt = r.cookies.get("refresh_token")
    assert rt

    # Evita cookies= por petición → usa el cookie jar del cliente
    client.cookies.set("refresh_token", rt)
    r2 = client.post("/api/v1/tenant/auth/refresh")
    assert r2.status_code == 200
    assert r2.cookies.get("refresh_token") != rt  # rotación


def test_logout_revokes_family(client, db, usuario_empresa_factory):
    u = usuario_empresa_factory(email="b@x.com", username="b", password="s3cr3t")  # noqa: F841
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "b", "password": "s3cr3t"},
    )
    rt = r.cookies.get("refresh_token")
    assert rt

    # Logout con cookie en el jar (no por petición)
    client.cookies.set("refresh_token", rt)
    client.post("/api/v1/tenant/auth/logout")

    # Reinyecta el RT antiguo y prueba refresh (debe fallar)
    client.cookies.set("refresh_token", rt)
    r2 = client.post("/api/v1/tenant/auth/refresh")
    assert r2.status_code == 401


def test_admin_csrf_endpoint(client):
    response = client.get("/api/v1/admin/auth/csrf")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    token = payload.get("csrfToken")
    assert isinstance(token, str) and token
    assert client.cookies.get("csrf_token") == token
