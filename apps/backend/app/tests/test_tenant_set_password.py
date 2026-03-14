from __future__ import annotations

from uuid import uuid4

from app.api.v1.tenant import auth as tenant_auth
from app.models.company.company_user import CompanyUser
from app.models.tenant import Tenant


def test_tenant_set_password_marks_first_company_admin_activation_for_onboarding(db, monkeypatch):
    tenant = Tenant(id=uuid4(), name="Demo Empresa", slug="demo-empresa")
    db.add(tenant)
    db.flush()

    user = CompanyUser(
        tenant_id=tenant.id,
        first_name="Franklin",
        last_name="Cashabamba",
        email="franklin@example.com",
        username="franklin",
        password_hash="old-hash",
        is_company_admin=True,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(tenant_auth, "verificar_token_email", lambda token, max_age: user.email)

    result = tenant_auth.tenant_set_password(
        tenant_auth.SetPasswordIn(token="valid-token", password="NewPassw0rd!"),
        db,
    )

    db.refresh(user)
    assert result["ok"] is True
    assert result["requires_onboarding"] is True
    assert user.is_verified is True
    assert user.password_hash != "old-hash"


def test_tenant_set_password_keeps_reset_flow_without_onboarding_for_verified_admin(
    db, monkeypatch
):
    tenant = Tenant(id=uuid4(), name="Demo Empresa", slug="demo-empresa")
    db.add(tenant)
    db.flush()

    user = CompanyUser(
        tenant_id=tenant.id,
        first_name="Franklin",
        last_name="Cashabamba",
        email="franklin@example.com",
        username="franklin",
        password_hash="old-hash",
        is_company_admin=True,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(tenant_auth, "verificar_token_email", lambda token, max_age: user.email)

    result = tenant_auth.tenant_set_password(
        tenant_auth.SetPasswordIn(token="valid-token", password="NewPassw0rd!"),
        db,
    )

    assert result["requires_onboarding"] is False
