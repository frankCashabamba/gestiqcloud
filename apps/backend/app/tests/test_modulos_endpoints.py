from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_modulos(db, usuario_empresa_factory):
    """Crea empresa+usuario, dos módulos activos y sus enlaces para pruebas.

    Devuelve tuple: (usuario, empresa, [mod1, mod2])
    """
    from app.models.core.modulo import AssignedModule, CompanyModule, Module

    usuario, tenant_from_factory = usuario_empresa_factory(
        empresa_name="Empresa Test Mods",
        username="mods_user",
        email="mods_user@example.com",
    )

    # Factory already created tenant
    tenant = tenant_from_factory

    # Crea dos módulos activos si no existen
    m1 = db.query(Module).filter(Module.name == "Ventas").first()
    if not m1:
        m1 = Module(
            name="Ventas",
            description="Ventas",
            active=True,
            initial_template="default",
            context_type="none",
        )
        db.add(m1)
    m2 = db.query(Module).filter(Module.name == "Facturacion").first()
    if not m2:
        m2 = Module(
            name="Facturacion",
            description="Facturación",
            active=True,
            initial_template="default",
            context_type="none",
        )
        db.add(m2)
    db.flush()

    # Vincula módulos contratados por el tenant
    for m in (m1, m2):
        exists = (
            db.query(CompanyModule)
            .filter(CompanyModule.tenant_id == tenant.id, CompanyModule.module_id == m.id)
            .first()
        )
        if not exists:
            db.add(CompanyModule(tenant_id=tenant.id, module_id=m.id, active=True))

    db.flush()

    # Asigna al usuario al menos un módulo para el endpoint /modulos/ (tenant)
    if not (
        db.query(AssignedModule)
        .filter(
            AssignedModule.tenant_id == tenant.id,
            AssignedModule.user_id == usuario.id,
            AssignedModule.module_id == m1.id,
        )
        .first()
    ):
        db.add(
            AssignedModule(
                tenant_id=tenant.id,
                user_id=usuario.id,
                module_id=m1.id,
                auto_view_module=True,
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
    assert {"id", "name", "active"}.issubset(first.keys())


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
    assert {"id", "name"}.issubset(data[0].keys())
