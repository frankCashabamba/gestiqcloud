"""Tests: POST /tenant/restaurant/orders/{id}/items rechaza productos no vendibles.

Sigue la convención de `test_restaurant_close.py` — invoca la función del
endpoint directamente con un `db` falso y `request` con tenant_id stubbeado.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


class _FakeRow:
    def __init__(self, *values):
        self._values = values

    def __getitem__(self, idx):
        return self._values[idx]


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeDb:
    """Stub de DB con respuestas pre-programadas por orden de SELECT."""

    def __init__(self, selects):
        self._selects = list(selects)
        self.executes: list[str] = []
        self.committed = False

    def execute(self, stmt, params=None):
        sql = str(stmt)
        self.executes.append(sql)
        if sql.lstrip().upper().startswith("SELECT"):
            row = self._selects.pop(0) if self._selects else None
            return _FakeResult(_FakeRow(*row) if row else None)
        raise AssertionError(f"unexpected mutation in failing-validation test: {sql}")

    def commit(self):
        self.committed = True


def _make_request():
    return SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": str(uuid4())}))


def _payload():
    from app.modules.restaurant.interface.http.tenant import OrderItemCreateIn

    return OrderItemCreateIn(
        product_id=uuid4(),
        product_name="X",
        qty=1,
        unit_price=10.0,
    )


@pytest.fixture
def patched_module(monkeypatch):
    from app.modules.restaurant.interface.http import tenant as t

    monkeypatch.setattr(t, "ensure_guc_from_request", lambda *a, **kw: None)
    return t


def test_add_item_rejects_when_product_is_raw_material(patched_module):
    t = patched_module
    db = _FakeDb(
        selects=[
            (uuid4(), "open"),
            (uuid4(), True, True),
        ]
    )
    with pytest.raises(HTTPException) as exc:
        t.add_order_item(str(uuid4()), _payload(), request=_make_request(), db=db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "product_not_sellable"


def test_add_item_rejects_when_product_inactive(patched_module):
    t = patched_module
    db = _FakeDb(
        selects=[
            (uuid4(), "open"),
            (uuid4(), False, False),
        ]
    )
    with pytest.raises(HTTPException) as exc:
        t.add_order_item(str(uuid4()), _payload(), request=_make_request(), db=db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "product_not_sellable"


def test_add_item_rejects_when_product_not_found_for_tenant(patched_module):
    t = patched_module
    db = _FakeDb(
        selects=[
            (uuid4(), "open"),
            None,
        ]
    )
    with pytest.raises(HTTPException) as exc:
        t.add_order_item(str(uuid4()), _payload(), request=_make_request(), db=db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "product_not_sellable"


def test_add_item_rejects_when_order_closed(patched_module):
    t = patched_module
    db = _FakeDb(selects=[(uuid4(), "paid")])
    with pytest.raises(HTTPException) as exc:
        t.add_order_item(str(uuid4()), _payload(), request=_make_request(), db=db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "order_is_closed"
