from __future__ import annotations

from uuid import uuid4

from app.models.auth.useradmis import SuperUser
from app.models.empresa.usuarioempresa import CompanyUser
from app.models.tenant import Tenant
from app.modules.usuarios.interface.http.admin import SetPasswordIn, set_password


def test_admin_set_password_updates_usuarioempresa_only(db):
    # Arrange: create a SuperUser and a CompanyUser
    su = SuperUser(username="owner", email="owner@example.com", password_hash="x")  # noqa: F841
    db.add(su)
    db.flush()

    # Create tenant (Tenant is now the primary entity, no tenant_id needed)
    tenant = Tenant(id=uuid4(), nombre="Test Co", slug="testco-t")
    db.add(tenant)
    db.flush()

    cu = CompanyUser(
        tenant_id=tenant.id,
        first_name="Admin",
        last_name="Test",
        email="admin@example.com",
        username="admin",
        password_hash="y",
        is_admin=True,
        active=True,
    )
    db.add(cu)
    db.commit()
    db.refresh(su)
    db.refresh(cu)

    old_su_hash = su.password_hash
    old_cu_hash = cu.password_hash

    # Act: call the admin endpoint function to set password for the tenant admin
    set_password(cu.id, SetPasswordIn(password="NewPassw0rd!"), db)

    # Assert: CompanyUser hash changed, SuperUser unchanged
    db.refresh(cu)
    db.refresh(su)
    assert cu.password_hash != old_cu_hash
    assert su.password_hash == old_su_hash


def test_admin_set_password_not_found(db):
    from fastapi import HTTPException

    try:
        set_password(999999, SetPasswordIn(password="NewPassw0rd!"), db)
        assert False, "expected HTTPException for missing user"
    except HTTPException as e:
        assert e.status_code == 404
