"""Tests del tenant context único (docs/security/tenant-context-contract.md).

Verifican que get_tenant_context resuelve scope/tenant/usuario desde los claims
y que las funciones lectoras legacy delegan en él de forma consistente.

Deterministas: se pasa request.state.access_claims explícito (dict), de modo
que get_tenant_context no necesita decodificar token real.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.tenant_context import TenantContext, get_tenant_context

TID = "00000000-0000-0000-0000-000000000002"
UID = "00000000-0000-0000-0000-000000000001"


def _req(access_claims=None, session=None, request_id=None, tenant_id_attr=None):
    state = SimpleNamespace()
    if access_claims is not None:
        state.access_claims = access_claims
    if session is not None:
        state.session = session
    if request_id is not None:
        state.request_id = request_id
    if tenant_id_attr is not None:
        state.tenant_id = tenant_id_attr
    return SimpleNamespace(state=state)


# --------------------------------------------------------------------------- #
# get_tenant_context: resolución de scope
# --------------------------------------------------------------------------- #
def test_scope_tenant_from_claims():
    ctx = get_tenant_context(
        _req({"tenant_id": TID, "user_id": UID, "kind": "tenant"})
    )
    assert isinstance(ctx, TenantContext)
    assert ctx.scope == "tenant"
    assert ctx.tenant_id == UUID(TID)
    assert ctx.user_id == UUID(UID)


def test_scope_admin_from_kind():
    ctx = get_tenant_context(_req({"user_id": UID, "kind": "admin", "is_superadmin": True}))
    assert ctx.scope == "admin"
    assert ctx.is_superadmin is True


def test_scope_public_when_no_identity():
    ctx = get_tenant_context(_req({}))  # dict vacío => no decodifica token
    assert ctx.scope == "public"
    assert ctx.tenant_id is None


def test_user_id_from_sub_alias():
    ctx = get_tenant_context(_req({"tenant_id": TID, "sub": UID, "kind": "tenant"}))
    assert ctx.user_id == UUID(UID)


def test_session_fallback_when_enabled():
    ctx = get_tenant_context(
        _req(access_claims={}, session={"tenant_id": TID, "tenant_user_id": UID})
    )
    assert ctx.tenant_id == UUID(TID)
    assert ctx.user_id == UUID(UID)


def test_session_fallback_disabled():
    ctx = get_tenant_context(
        _req(access_claims={}, session={"tenant_id": TID}),
        allow_session_fallback=False,
    )
    assert ctx.tenant_id is None
    assert ctx.scope == "public"


def test_invalid_uuid_becomes_none():
    ctx = get_tenant_context(_req({"tenant_id": "not-a-uuid", "kind": "tenant"}))
    assert ctx.tenant_id is None
    assert ctx.scope == "public"  # sin tenant válido y kind!=admin


def test_request_id_propagated():
    ctx = get_tenant_context(_req({"tenant_id": TID, "kind": "tenant"}, request_id="abc-123"))
    assert ctx.request_id == "abc-123"


# --------------------------------------------------------------------------- #
# Las funciones lectoras legacy delegan en la puerta
# --------------------------------------------------------------------------- #
def test_get_tenant_uuid_delegates():
    from app.core.dependencies import get_tenant_uuid

    out = get_tenant_uuid(_req({"tenant_id": TID, "kind": "tenant"}))
    assert out == UUID(TID)


def test_get_tenant_uuid_raises_without_tenant():
    from app.core.dependencies import get_tenant_uuid

    with pytest.raises(HTTPException) as exc:
        get_tenant_uuid(_req({}))
    assert exc.value.status_code == 401


def test_tenant_id_from_request_str_or_none():
    from app.db.rls import tenant_id_from_request

    assert tenant_id_from_request(_req({"tenant_id": TID, "kind": "tenant"})) == TID
    assert tenant_id_from_request(_req({})) is None
