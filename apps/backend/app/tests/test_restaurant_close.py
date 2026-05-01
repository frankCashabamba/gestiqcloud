from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


class _DbMustNotMutate:
    def execute(self, *args, **kwargs):  # pragma: no cover - only used on failure
        raise AssertionError("restaurant close must not touch orders until POS/billing is integrated")

    def commit(self):  # pragma: no cover - only used on failure
        raise AssertionError("restaurant close must not commit until POS/billing is integrated")


def test_restaurant_close_is_blocked_until_pos_billing_integration(monkeypatch):
    from app.modules.restaurant.interface.http import tenant as restaurant_tenant

    monkeypatch.setattr(restaurant_tenant, "ensure_guc_from_request", lambda *args, **kwargs: None)
    request = SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": str(uuid4())}))

    with pytest.raises(HTTPException) as exc:
        restaurant_tenant.close_order(str(uuid4()), request=request, db=_DbMustNotMutate())

    assert exc.value.status_code == 501
    assert exc.value.detail == "restaurant_close_requires_pos_billing_integration"
