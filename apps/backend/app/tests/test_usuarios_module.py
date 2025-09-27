
import pytest
from fastapi.testclient import TestClient

TENANT_LOGIN = {
    "identificador": "tenant_admin@example.com",
    "password": "tenant123",
}


@pytest.fixture
def tenant_headers(client: TestClient, usuario_empresa_factory, seed_tenant_context):
    usuario, empresa = seed_tenant_context
    # login
    r = client.post("/api/v1/tenant/auth/login", json={
        "identificador": usuario.email,
        "password": "tenant123",
    })
    assert r.status_code == 200, r.text
    token = r.json().get("access_token")
    assert token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_tenant_context(db, usuario_empresa_factory):
    from app.models.core.modulo import Modulo, EmpresaModulo
    from app.models.empresa.rolempresas import RolEmpresa
    from app.models.empresa.usuarioempresa import UsuarioEmpresa

    usuario, empresa = usuario_empresa_factory(email="tenant_admin@example.com", username="tenantadmin")
    usuario.is_verified = True
    db.add(usuario)

    modulo_a = (
        db.query(Modulo)
        .filter(Modulo.nombre == "Ventas")
        .first()
    )
    if not modulo_a:
        modulo_a = Modulo(
            nombre="Ventas",
            descripcion="Modulo de ventas",
            activo=True,
            plantilla_inicial="default",
            context_type="none",
        )
        db.add(modulo_a)

    modulo_b = (
        db.query(Modulo)
        .filter(Modulo.nombre == "Compras")
        .first()
    )
    if not modulo_b:
        modulo_b = Modulo(
            nombre="Compras",
            descripcion="Modulo de compras",
            activo=True,
            plantilla_inicial="default",
            context_type="none",
        )
        db.add(modulo_b)

    db.flush()

    for modulo in (modulo_a, modulo_b):
        exists_link = (
            db.query(EmpresaModulo)
            .filter_by(empresa_id=empresa.id, modulo_id=modulo.id)
            .first()
        )
        if not exists_link:
            db.add(EmpresaModulo(empresa_id=empresa.id, modulo_id=modulo.id, activo=True))

    rol_admin = (
        db.query(RolEmpresa)
        .filter_by(empresa_id=empresa.id, nombre="Super Admin")
        .first()
    )
    if not rol_admin:
        rol_admin = RolEmpresa(
            empresa_id=empresa.id,
            nombre="Super Admin",
            descripcion="Acceso total",
            permisos={},
        )
        db.add(rol_admin)
    else:
        rol_admin.descripcion = "Acceso total"
        if not rol_admin.permisos:
            rol_admin.permisos = {}

    rol_editor = (
        db.query(RolEmpresa)
        .filter_by(empresa_id=empresa.id, nombre="Editor")
        .first()
    )
    if not rol_editor:
        rol_editor = RolEmpresa(
            empresa_id=empresa.id,
            nombre="Editor",
            descripcion="Puede editar",
            permisos={},
        )
        db.add(rol_editor)
    else:
        rol_editor.descripcion = "Puede editar"
        if not rol_editor.permisos:
            rol_editor.permisos = {}

    extra_admins = (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.empresa_id == empresa.id,
            UsuarioEmpresa.id != usuario.id,
            UsuarioEmpresa.es_admin_empresa.is_(True),
        )
        .all()
    )
    for other_admin in extra_admins:
        other_admin.es_admin_empresa = False

    db.commit()
    db.refresh(usuario)
    db.refresh(empresa)
    return usuario, empresa


def test_listar_usuarios(client: TestClient, tenant_headers):
    r = client.get("/api/v1/tenant/usuarios", headers=tenant_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(u["es_admin_empresa"] for u in data)


def test_listar_modulos(client: TestClient, tenant_headers):
    r = client.get("/api/v1/tenant/usuarios/modulos", headers=tenant_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


def test_listar_roles(client: TestClient, tenant_headers):
    r = client.get("/api/v1/tenant/usuarios/roles", headers=tenant_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


def test_check_username_public(client: TestClient):
    r = client.get("/api/v1/usuarios/check-username/algunusuario")
    assert r.status_code in (200, 400)


def test_crear_usuario_estandar(client: TestClient, tenant_headers):
    modules = client.get("/api/v1/tenant/usuarios/modulos", headers=tenant_headers).json()
    roles = client.get("/api/v1/tenant/usuarios/roles", headers=tenant_headers).json()
    payload = {
        "nombre_encargado": "Juan",
        "apellido_encargado": "Perez",
        "email": "juan@example.com",
        "username": "juanp",
        "password": "Secret123!",
        "es_admin_empresa": False,
        "modulos": [modules[0]["id"]],
        "roles": [roles[0]["id"]],
        "activo": True,
    }
    r = client.post("/api/v1/tenant/usuarios", json=payload, headers=tenant_headers)
    assert r.status_code == 201, r.text
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
        "activo": True,
    }
    r = client.post("/api/v1/tenant/usuarios", json=payload, headers=tenant_headers)
    assert r.status_code == 201, r.text
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
        "activo": True,
    }
    r = client.post("/api/v1/tenant/usuarios", json=payload, headers=tenant_headers)
    assert r.status_code == 201
    usuario_id = r.json()["id"]

    update = {
        "apellido_encargado": "Actualizada",
        "activo": False,
        "modulos": [],
        "roles": [],
    }
    r = client.patch(f"/api/v1/tenant/usuarios/{usuario_id}", json=update, headers=tenant_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["apellido_encargado"] == "Actualizada"
    assert data["activo"] is False


def test_no_permite_eliminar_ultimo_admin(client: TestClient, tenant_headers):
    usuarios = client.get("/api/v1/tenant/usuarios", headers=tenant_headers).json()
    admin = next(u for u in usuarios if u["es_admin_empresa"])
    r = client.patch(
        f"/api/v1/tenant/usuarios/{admin['id']}",
        json={"es_admin_empresa": False},
        headers=tenant_headers,
    )
    assert r.status_code == 400
