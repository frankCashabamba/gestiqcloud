"""Tests de permisos granulares en endpoints de accounting.

Verifica que `require_permission` rechaza (403) cuando el usuario no tiene la
permission key correspondiente y permite cuando la tiene.

Constants under test (apps/backend/app/core/permissions.py):
- accounting.entry.create
- accounting.entry.post
- accounting.entry.cancel
- accounting.account.manage
- accounting.reports.read
- accounting.period.manage
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.access_guard import with_access_claims
from app.core.authz import require_permission
from app.core.permissions import (
    PERM_ACCOUNTING_ACCOUNT_MANAGE,
    PERM_ACCOUNTING_ENTRY_CANCEL,
    PERM_ACCOUNTING_ENTRY_CREATE,
    PERM_ACCOUNTING_ENTRY_POST,
    PERM_ACCOUNTING_PERIOD_MANAGE,
    PERM_ACCOUNTING_REPORTS_READ,
)


ALL_PERMS = [
    PERM_ACCOUNTING_ENTRY_CREATE,
    PERM_ACCOUNTING_ENTRY_POST,
    PERM_ACCOUNTING_ENTRY_CANCEL,
    PERM_ACCOUNTING_ACCOUNT_MANAGE,
    PERM_ACCOUNTING_REPORTS_READ,
    PERM_ACCOUNTING_PERIOD_MANAGE,
]


def test_permission_constants_have_expected_keys():
    assert PERM_ACCOUNTING_ENTRY_CREATE == "accounting.entry.create"
    assert PERM_ACCOUNTING_ENTRY_POST == "accounting.entry.post"
    assert PERM_ACCOUNTING_ENTRY_CANCEL == "accounting.entry.cancel"
    assert PERM_ACCOUNTING_ACCOUNT_MANAGE == "accounting.account.manage"
    assert PERM_ACCOUNTING_REPORTS_READ == "accounting.reports.read"
    assert PERM_ACCOUNTING_PERIOD_MANAGE == "accounting.period.manage"


def _build_app(perm: str, claims: dict):
    """Construye una mini-app FastAPI con un endpoint protegido por `perm`."""
    app = FastAPI()

    def _claims_override():
        return claims

    @app.get("/protected", dependencies=[Depends(require_permission(perm))])
    def protected():
        return {"ok": True}

    app.dependency_overrides[with_access_claims] = _claims_override
    return app


def test_require_permission_rejects_without_grant():
    for perm in ALL_PERMS:
        claims = {
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "user_id": "22222222-2222-2222-2222-222222222222",
            "permissions": {},
        }
        app = _build_app(perm, claims)
        client = TestClient(app)
        r = client.get("/protected")
        assert r.status_code == 403, f"perm {perm} should reject"
        body = r.json()
        assert body["detail"]["missing_permission"] == perm


def test_require_permission_accepts_when_granted():
    for perm in ALL_PERMS:
        claims = {
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "user_id": "22222222-2222-2222-2222-222222222222",
            "permissions": {perm: True},
        }
        app = _build_app(perm, claims)
        client = TestClient(app)
        r = client.get("/protected")
        assert r.status_code == 200, f"perm {perm} should accept"


def test_company_admin_bypass():
    """Un company admin no necesita permisos explícitos."""
    claims = {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "is_company_admin": True,
        "permissions": {},
    }
    app = _build_app(PERM_ACCOUNTING_PERIOD_MANAGE, claims)
    client = TestClient(app)
    assert client.get("/protected").status_code == 200
