import pytest
from fastapi.testclient import TestClient

TENANT_LOGIN = {
    "identificador": "tenant_admin@example.com",
    "password": "tenant123",
}


@pytest.fixture
def tenant_headers(client: TestClient, usuario_empresa_factory, seed_tenant_context):
    import json
    import base64

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
    from app.models.core.modulo import EmpresaModulo, Modulo
    from app.models.empresa.rolempresas import RolEmpresa
    from app.models.empresa.usuarioempresa import UsuarioEmpresa
    from app.models.empresa.usuario_rolempresa import UsuarioRolempresa

    usuario, tenant = usuario_empresa_factory(
        email="tenant_admin@example.com", username="tenantadmin"
    )
    usuario.is_verified = True
    usuario.es_admin_empresa = True  # Make sure admin flag is set
    db.add(usuario)
    # Tenant already created by factory

    modulo_a = db.query(Modulo).filter(Modulo.name == "Ventas").first()
    if not modulo_a:
        modulo_a = Modulo(
            name="Ventas",
            description="Modulo de ventas",
            active=True,
            plantilla_inicial="default",
            context_type="none",
        )
        db.add(modulo_a)

    modulo_b = db.query(Modulo).filter(Modulo.name == "Compras").first()
    if not modulo_b:
        modulo_b = Modulo(
            name="Compras",
            description="Modulo de compras",
            active=True,
            plantilla_inicial="default",
            context_type="none",
        )
        db.add(modulo_b)

    db.flush()

    for modulo in (modulo_a, modulo_b):
        exists_link = (
            db.query(EmpresaModulo).filter_by(tenant_id=tenant.id, modulo_id=modulo.id).first()
        )
        if not exists_link:
            db.add(EmpresaModulo(tenant_id=tenant.id, modulo_id=modulo.id, active=True))

    rol_admin = db.query(RolEmpresa).filter_by(tenant_id=tenant.id, name="Super Admin").first()
    if not rol_admin:
        rol_admin = RolEmpresa(
            tenant_id=tenant.id,
            name="Super Admin",
            description="Acceso total",
            permisos={
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
        if not rol_admin.permisos:
            rol_admin.permisos = {}

    rol_editor = db.query(RolEmpresa).filter_by(tenant_id=tenant.id, name="Editor").first()
    if not rol_editor:
        rol_editor = RolEmpresa(
            tenant_id=tenant.id,
            name="Editor",
            description="Puede editar",
            permisos={
                "read": True,
                "write": True,
            },
        )
        db.add(rol_editor)
    else:
        rol_editor.description = "Puede editar"
        if not rol_editor.permisos:
            rol_editor.permisos = {}

    db.flush()

    # Assign admin role to the main user
    existing_rel = (
        db.query(UsuarioRolempresa).filter_by(usuario_id=usuario.id, tenant_id=tenant.id).first()
    )
    if not existing_rel:
        db.add(
            UsuarioRolempresa(
                usuario_id=usuario.id,
                tenant_id=tenant.id,
                rol_id=rol_admin.id,
                activo=True,
            )
        )

    extra_admins = (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.tenant_id == tenant.id,
            UsuarioEmpresa.id != usuario.id,
            UsuarioEmpresa.es_admin_empresa.is_(True),
        )
        .all()
    )
    for other_admin in extra_admins:
        other_admin.es_admin_empresa = False

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
        "nombre_encargado": "Juan",
        "apellido_encargado": "Perez",
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
        "nombre_encargado": "Ana",
        "apellido_encargado": "Admin",
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
        "nombre_encargado": "Maria",
        "apellido_encargado": "Tester",
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
        "apellido_encargado": "Actualizada",
        "active": False,
        "modulos": [],
        "roles": [],
    }
    r = client.patch(f"/api/v1/tenant/usuarios/{usuario_id}", json=update, headers=tenant_headers)
    assert r.status_code == 200, f"Expected 200 on update, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["apellido_encargado"] == "Actualizada"
    assert data["active"] is False


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
