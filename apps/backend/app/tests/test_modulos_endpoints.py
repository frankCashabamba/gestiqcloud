from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_modulos(db, usuario_empresa_factory):
    """Crea empresa+usuario, dos módulos activos y sus enlaces para pruebas.

    Devuelve tuple: (usuario, empresa, [mod1, mod2])
    """
    from app.models.core.modulo import EmpresaModulo, Modulo, ModuloAsignado

    usuario, tenant_from_factory = usuario_empresa_factory(
        empresa_name="Empresa Test Mods",
        username="mods_user",
        email="mods_user@example.com",
    )

    # Factory already created tenant
    tenant = tenant_from_factory

    # Crea dos módulos activos si no existen
    m1 = db.query(Modulo).filter(Modulo.name == "Ventas").first()
    if not m1:
        m1 = Modulo(
            name="Ventas",
            descripcion="Ventas",
            activo=True,
            plantilla_inicial="default",
            context_type="none",
        )
        db.add(m1)
    m2 = db.query(Modulo).filter(Modulo.name == "Facturacion").first()
    if not m2:
        m2 = Modulo(
            name="Facturacion",
            descripcion="Facturación",
            activo=True,
            plantilla_inicial="default",
            context_type="none",
        )
        db.add(m2)
    db.flush()

    # Vincula módulos contratados por el tenant
    for m in (m1, m2):
        exists = (
            db.query(EmpresaModulo)
            .filter(EmpresaModulo.tenant_id == tenant.id, EmpresaModulo.modulo_id == m.id)
            .first()
        )
        if not exists:
            db.add(EmpresaModulo(tenant_id=tenant.id, modulo_id=m.id, activo=True))

    db.flush()

    # Asigna al usuario al menos un módulo para el endpoint /modulos/ (tenant)
    if not (
        db.query(ModuloAsignado)
        .filter(
            ModuloAsignado.tenant_id == tenant.id,
            ModuloAsignado.usuario_id == usuario.id,
            ModuloAsignado.modulo_id == m1.id,
        )
        .first()
    ):
        db.add(
            ModuloAsignado(
                tenant_id=tenant.id,
                usuario_id=usuario.id,
                modulo_id=m1.id,
                ver_modulo_auto=True,
            )
        )

    db.commit()
    db.refresh(usuario)
    db.refresh(tenant)
    return usuario, tenant, [m1, m2]


def test_public_modulos_por_empresa_returns_array(client: TestClient, seeded_modulos):
    _, tenant, _ = seeded_modulos
    r = client.get(f"/api/v1/modulos/empresa/{tenant.slug}/seleccionables")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Estructura mínima esperada por el frontend
    first = data[0]
    assert set(["id", "name", "active"]).issubset(first.keys())


def test_tenant_modulos_list_returns_array(client: TestClient, seeded_modulos):
    usuario, _, _ = seeded_modulos
    # Login tenant
    rlogin = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": usuario.email, "password": "tenant123"},
    )
    assert rlogin.status_code == 200, rlogin.text
    token = rlogin.json().get("access_token")
    assert token

    r = client.get("/api/v1/modulos/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    # Debe traer al menos el módulo asignado al usuario
    assert len(data) >= 1
    assert set(["id", "name"]).issubset(data[0].keys())
