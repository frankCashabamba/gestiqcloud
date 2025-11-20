#!/usr/bin/env python
import sys

sys.path.insert(0, ".")


def test_debug():
    import uuid

    from fastapi.testclient import TestClient

    from app.config.database import Base, SessionLocal, engine
    from app.tests.conftest import (
        _ensure_default_tenant,
        _ensure_sqlite_stub_tables,
        _ensure_test_env,
        _load_all_models,
        _prune_pg_only_tables,
        _recreate_sqlite_db_if_needed,
    )

    _ensure_test_env()
    _recreate_sqlite_db_if_needed()
    _load_all_models()
    _prune_pg_only_tables(Base.metadata)
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_stub_tables(engine)
    _ensure_default_tenant(engine)

    from app.main import app

    client = TestClient(app)

    # Create a test user

    db = SessionLocal()

    from app.models.empresa.usuarioempresa import UsuarioEmpresa
    from app.models.tenant import Tenant
    from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher

    hasher = PasslibPasswordHasher()

    # Create tenant
    tenant = Tenant(id=uuid.uuid4(), nombre="Test Tenant", slug="test-slug")
    db.add(tenant)
    db.flush()

    # Create user
    usuario = UsuarioEmpresa(
        tenant_id=tenant.id,
        nombre_encargado="Test",
        apellido_encargado="User",
        email="test@example.com",
        username="testuser",
        es_admin_empresa=True,
        password_hash=hasher.hash("password123"),
        activo=True,
        is_verified=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    db.refresh(tenant)

    print(
        f"Created user: {usuario.id}, tenant: {tenant.id}, activo: {usuario.activo}, is_active: {usuario.is_active}"
    )

    # Try to login
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={
            "identificador": usuario.email,
            "password": "password123",
        },
    )
    print(f"Login response: {r.status_code}")
    print(f"Login body: {r.text[:200]}")

    if r.status_code == 200:
        token = r.json().get("access_token")
        print(f"Token: {token[:50]}...")

        # Try to list usuarios
        headers = {"Authorization": f"Bearer {token}"}
        r2 = client.get("/api/v1/tenant/usuarios", headers=headers)
        print(f"List usuarios response: {r2.status_code}")
        print(f"List usuarios body: {r2.text[:200]}")

    db.close()


if __name__ == "__main__":
    test_debug()
