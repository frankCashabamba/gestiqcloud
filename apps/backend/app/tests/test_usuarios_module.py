import pytest
from fastapi.testclient import TestClient

TENANT_LOGIN = {
    "identificador": "tenant_admin@example.com",
    "password": "tenant123",
}


@pytest.fixture
def tenant_headers(client: TestClient, usuario_empresa_factory, seed_tenant_context):
    import base64
    import json

    usuario, tenant = seed_tenant_context
    # login
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={
            "identificador": usuario.email,
            "password": "tenant123",
        },
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token")
    assert token, f"No token in response: {data}"

    # Debug: decode and print token payload
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload = parts[1]
            # Add padding if needed
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += "=" * padding
            decoded = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded)
            print(f"\n[DEBUG] Token payload: {json.dumps(payload_data, indent=2)}")
            print(f"[DEBUG] Token payload keys: {list(payload_data.keys())}")
            print(f"[DEBUG] has 'kind': {'kind' in payload_data}")
            print(f"[DEBUG] has 'sub': {'sub' in payload_data}")
            print(f"[DEBUG] has 'es_admin_empresa': {'es_admin_empresa' in payload_data}")
            print(f"[DEBUG] has 'permisos': {'permisos' in payload_data}")
    except Exception as e:
        print(f"\n[DEBUG] Could not decode token: {e}")

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_tenant_context(db, usuario_empresa_factory):
    from app.models.core.modulo import CompanyModule, Module
    from app.models.empresa.rolempresas import CompanyRole
    from app.models.empresa.usuario_rolempresa import CompanyUserRole
    from app.models.empresa.usuarioempresa import CompanyUser

    usuario, tenant = usuario_empresa_factory(
        email="tenant_admin@example.com", username="tenantadmin"
    )
    usuario.is_verified = True
    usuario.is_company_admin = True  # Make sure admin flag is set
    db.add(usuario)
    # Tenant already created by factory

    modulo_a = db.query(Module).filter(Module.name == "Ventas").first()
    if not modulo_a:
        modulo_a = Module(
            name="Ventas",
            description="Modulo de ventas",
            active=True,
            initial_template="default",
            context_type="none",
        )
        db.add(modulo_a)

    modulo_b = db.query(Module).filter(Module.name == "Compras").first()
    if not modulo_b:
        modulo_b = Module(
            name="Compras",
            description="Modulo de compras",
            active=True,
            initial_template="default",
            context_type="none",
        )
        db.add(modulo_b)

    db.flush()

    for modulo in (modulo_a, modulo_b):
        exists_link = (
            db.query(CompanyModule).filter_by(tenant_id=tenant.id, module_id=modulo.id).first()
        )
        if not exists_link:
            db.add(CompanyModule(tenant_id=tenant.id, module_id=modulo.id, active=True))

    rol_admin = db.query(CompanyRole).filter_by(tenant_id=tenant.id, name="Super Admin").first()
    if not rol_admin:
        rol_admin = CompanyRole(
            tenant_id=tenant.id,
            name="Super Admin",
            description="Acceso total",
            permissions={
                "usuarios": {"create": True, "update": True, "delete": True, "set_password": True},
                "admin": True,
                "write": True,
                "read": True,
                "manage_users": True,
                "manage_settings": True,
                "manage_roles": True,
                "manage_modules": True,
            },
        )
        db.add(rol_admin)
    else:
        rol_admin.description = "Acceso total"
        if not rol_admin.permissions:
            rol_admin.permissions = {}

    rol_editor = db.query(CompanyRole).filter_by(tenant_id=tenant.id, name="Editor").first()
    if not rol_editor:
        rol_editor = CompanyRole(
            tenant_id=tenant.id,
            name="Editor",
            description="Puede editar",
            permissions={
                "read": True,
                "write": True,
            },
        )
        db.add(rol_editor)
    else:
        rol_editor.description = "Puede editar"
        if not rol_editor.permissions:
            rol_editor.permissions = {}

    db.flush()

    # Assign admin role to the main user
    existing_rel = (
        db.query(CompanyUserRole).filter_by(user_id=usuario.id, tenant_id=tenant.id).first()
    )
    if not existing_rel:
        db.add(
            CompanyUserRole(
                user_id=usuario.id,
                tenant_id=tenant.id,
                role_id=rol_admin.id,
                active=True,
            )
        )

    extra_admins = (
        db.query(CompanyUser)
        .filter(
            CompanyUser.tenant_id == tenant.id,
            CompanyUser.id != usuario.id,
            CompanyUser.is_company_admin.is_(True),
        )
        .all()
    )
    for other_admin in extra_admins:
        other_admin.is_company_admin = False

    db.commit()
    db.refresh(usuario)
    db.refresh(tenant)
    return usuario, tenant


def test_listar_usuarios(client: TestClient, tenant_headers):
    r = client.get("/api/v1/tenant/usuarios", headers=tenant_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert any(u["es_admin_empresa"] for u in data), "No admin user found in list"


def test_listar_modulos(client: TestClient, tenant_headers):
    r = client.get("/api/v1/tenant/usuarios/modulos", headers=tenant_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert len(data) >= 1, f"Expected at least 1 modulo, got {len(data)}"


def test_listar_roles(client: TestClient, tenant_headers):
    r = client.get("/api/v1/tenant/usuarios/roles", headers=tenant_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert len(data) >= 1, f"Expected at least 1 role, got {len(data)}"


def test_check_username_public(client: TestClient, db):
    r = client.get("/api/v1/usuarios/check-username/algunusuario")
    assert r.status_code in (200, 400)


def test_crear_usuario_estandar(client: TestClient, tenant_headers):
    modules = client.get("/api/v1/tenant/usuarios/modulos", headers=tenant_headers).json()
    roles = client.get("/api/v1/tenant/usuarios/roles", headers=tenant_headers).json()

    assert len(modules) > 0, "No modules available"
    assert len(roles) > 0, "No roles available"

    payload = {
        "first_name": "Juan",
        "last_name": "Perez",
        "email": "juan@example.com",
        "username": "juanp",
        "password": "Secret123!",
        "es_admin_empresa": False,
        "modulos": [modules[0]["id"]],
        "roles": [roles[0]["id"]],
        "active": True,
    }
    r = client.post("/api/v1/tenant/usuarios", json=payload, headers=tenant_headers)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["es_admin_empresa"] is False
    assert data["modulos"] == payload["modulos"]
    assert data["roles"] == payload["roles"]


def test_crear_usuario_admin(client: TestClient, tenant_headers):
    payload = {
        "first_name": "Ana",
        "last_name": "Admin",
        "email": "ana.admin@example.com",
        "username": "anaadmin",
        "password": "Secret123!",
        "es_admin_empresa": True,
        "modulos": [],
        "roles": [],
        "active": True,
    }
    r = client.post("/api/v1/tenant/usuarios", json=payload, headers=tenant_headers)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["es_admin_empresa"] is True
    # Admin obtiene todos los módulos contratados
    mods = client.get("/api/v1/tenant/usuarios/modulos", headers=tenant_headers).json()
    assert set(data["modulos"]) == {m["id"] for m in mods}


def test_actualizar_usuario(client: TestClient, tenant_headers):
    payload = {
        "first_name": "Maria",
        "last_name": "Tester",
        "email": "maria.tester@example.com",
        "username": "mariat",
        "password": "Secret123!",
        "es_admin_empresa": False,
        "modulos": [],
        "roles": [],
        "active": True,
    }
    r = client.post("/api/v1/tenant/usuarios", json=payload, headers=tenant_headers)
    assert r.status_code == 201, f"Expected 201 on create, got {r.status_code}: {r.text}"
    usuario_id = r.json()["id"]

    update = {
        "last_name": "Actualizada",
        "active": False,
        "modulos": [],
        "roles": [],
    }
    r = client.patch(f"/api/v1/tenant/usuarios/{usuario_id}", json=update, headers=tenant_headers)
    assert r.status_code == 200, f"Expected 200 on update, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["apellido_encargado"] == "Actualizada"
    assert data["activo"] is False


def test_no_permite_eliminar_ultimo_admin(client: TestClient, tenant_headers):
    usuarios = client.get("/api/v1/tenant/usuarios", headers=tenant_headers).json()
    admin = next((u for u in usuarios if u["es_admin_empresa"]), None)
    assert admin is not None, "No admin user found"

    r = client.patch(
        f"/api/v1/tenant/usuarios/{admin['id']}",
        json={"es_admin_empresa": False},
        headers=tenant_headers,
    )
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
