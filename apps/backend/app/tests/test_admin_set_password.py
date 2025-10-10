from __future__ import annotations

from app.modules.usuarios.interface.http.admin import set_password, SetPasswordIn
from app.models.auth.useradmis import SuperUser
from app.models.empresa.usuarioempresa import UsuarioEmpresa


def test_admin_set_password_updates_usuarioempresa_only(db):
    # Arrange: create a SuperUser and a UsuarioEmpresa
    su = SuperUser(username="owner", email="owner@example.com", password_hash="x")
    db.add(su)
    db.flush()

    ue = UsuarioEmpresa(
        empresa_id=1,
        nombre_encargado="Admin",
        apellido_encargado="Test",
        email="admin@example.com",
        username="admin",
        password_hash="y",
        es_admin_empresa=True,
        activo=True,
    )
    db.add(ue)
    db.commit()
    db.refresh(su)
    db.refresh(ue)

    old_su_hash = su.password_hash
    old_ue_hash = ue.password_hash

    # Act: call the admin endpoint function to set password for the tenant admin
    set_password(ue.id, SetPasswordIn(password="NewPassw0rd!"), db)

    # Assert: UsuarioEmpresa hash changed, SuperUser unchanged
    db.refresh(ue)
    db.refresh(su)
    assert ue.password_hash != old_ue_hash
    assert su.password_hash == old_su_hash


def test_admin_set_password_not_found(db):
    from fastapi import HTTPException

    try:
        set_password(999999, SetPasswordIn(password="NewPassw0rd!"), db)
        assert False, "expected HTTPException for missing user"
    except HTTPException as e:
        assert e.status_code == 404

