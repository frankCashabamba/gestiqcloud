"""Tests del contrato de auth única (docs/security/auth-contract.md).

Verifican que:
- la única puerta de validación es with_access_claims y los wrappers derivan de ella;
- los guards de scope/permiso se comportan según contrato;
- los símbolos legacy eliminados durante la unificación (2026-06-09) no reaparecen.

Son tests unitarios deterministas (no requieren BD ni red).
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


# --------------------------------------------------------------------------- #
# 1. Mapeo de claims -> AuthenticatedUser (protected.py)
# --------------------------------------------------------------------------- #
def test_claims_to_user_tenant():
    from app.modules.identity.interface.http.protected import _claims_to_user

    user = _claims_to_user(
        {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "tenant_id": "00000000-0000-0000-0000-000000000002",
            "kind": "tenant",
            "is_company_admin": True,
            "permissions": {"x": True},
            "nombre": "Ada",
        }
    )
    assert str(user.user_id) == "00000000-0000-0000-0000-000000000001"
    assert user.user_type == "tenant"
    assert user.is_company_admin is True
    # permisos acepta tanto "permisos" como "permissions"
    assert user.permisos == {"x": True}
    assert user.name == "Ada"


def test_claims_to_user_admin():
    from app.modules.identity.interface.http.protected import _claims_to_user

    user = _claims_to_user(
        {
            "user_id": "00000000-0000-0000-0000-000000000009",
            "kind": "admin",
            "is_superadmin": True,
        }
    )
    assert user.user_type == "admin"
    assert user.is_superadmin is True


# --------------------------------------------------------------------------- #
# 2. require_scope / require_permission (authz.py)
# --------------------------------------------------------------------------- #
def test_require_scope_admin_accepts_admin_rejects_tenant():
    from app.core.authz import require_scope

    dep = require_scope("admin")
    assert dep(claims={"kind": "admin"}) == {"kind": "admin"}

    with pytest.raises(HTTPException) as exc:
        dep(claims={"kind": "tenant", "is_company_admin": True})
    assert exc.value.status_code == 403


def test_require_permission_bypassed_by_company_admin():
    from app.core.authz import require_permission

    dep = require_permission("accounting.account.manage")
    # company-admin pasa cualquier permiso
    assert dep(claims={"is_company_admin": True})
    # usuario sin el permiso es rechazado
    with pytest.raises(HTTPException) as exc:
        dep(claims={"permissions": {}})
    assert exc.value.status_code == 403


def test_require_permission_accepts_nested_permission_dict():
    from app.core.authz import require_permission

    dep = require_permission("notifications:read")

    assert dep(claims={"permissions": {"notifications": {"read": True}}})


def test_require_permission_accepts_colon_and_dotted_aliases():
    from app.core.authz import require_permission

    assert require_permission("pos.view")(claims={"permissions": {"pos:read": True}})
    assert require_permission("pos.receipt.pay")(
        claims={"permissions": {"pos.receipt": {"pay": True}}}
    )
    assert require_permission("accounting.entry.create")(
        claims={"permissions": {"accounting:entry": True}}
    )


# --------------------------------------------------------------------------- #
# 3. get_current_user (wrapper dict) deriva de los claims y valida tenant UUID
# --------------------------------------------------------------------------- #
def _fake_request(claims):
    return SimpleNamespace(state=SimpleNamespace(access_claims=claims))


def test_get_current_user_dict_from_claims():
    from app.core.auth_dependencies import get_current_user

    req = _fake_request(
        {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "tenant_id": "00000000-0000-0000-0000-000000000002",
            "roles": ["r1"],
        }
    )
    out = get_current_user(req, db=None)
    assert out["user_id"] == "00000000-0000-0000-0000-000000000001"
    assert out["tenant_id"] == "00000000-0000-0000-0000-000000000002"
    assert out["roles"] == ["r1"]


def test_get_current_user_rejects_invalid_tenant():
    from app.core.auth_dependencies import get_current_user

    req = _fake_request({"user_id": "u", "tenant_id": "not-a-uuid"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(req, db=None)
    assert exc.value.status_code == 403


def test_middleware_tenant_is_shim_of_auth_dependencies():
    """middleware/tenant.py debe re-exportar exactamente, sin lógica propia."""
    from app.core import auth_dependencies
    from app.middleware import tenant

    assert tenant.get_current_user is auth_dependencies.get_current_user
    assert tenant.ensure_tenant is auth_dependencies.ensure_tenant


# --------------------------------------------------------------------------- #
# 4. Anti-regresión: los símbolos legacy eliminados no deben reaparecer
# --------------------------------------------------------------------------- #
def test_security_cookies_module_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.core.security_cookies")


def test_core_security_stub_removed():
    security = importlib.import_module("app.core.security")
    assert not hasattr(security, "get_current_active_tenant_user")


def test_protected_no_longer_exposes_own_decoder():
    protected = importlib.import_module("app.modules.identity.interface.http.protected")
    # decode_token / oauth2_scheme eran la puerta de decodificación paralela
    assert not hasattr(protected, "oauth2_scheme")
    assert not hasattr(protected, "decode_token")
