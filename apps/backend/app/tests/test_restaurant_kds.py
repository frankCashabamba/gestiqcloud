"""Tests: KDS endpoints — flujo pending -> preparing -> ready -> served."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _SelectDb:
    """Devuelve `rows` para cualquier SELECT y registra mutaciones."""

    def __init__(self, rows):
        self._rows = rows
        self.mutations: list[tuple[str, dict]] = []
        self.committed = False

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if sql.lstrip().upper().startswith("SELECT"):
            return _FakeResult(self._rows)
        self.mutations.append((sql, dict(params or {})))
        return _FakeResult([])

    def commit(self):
        self.committed = True


def _request():
    return SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": str(uuid4())}))


@pytest.fixture
def t(monkeypatch):
    from app.modules.restaurant.interface.http import tenant as mod

    monkeypatch.setattr(mod, "ensure_guc_from_request", lambda *a, **kw: None)
    return mod


def test_kds_list_groups_items_by_order(t):
    now = datetime.now(UTC)
    order_id = uuid4()
    rows = [
        (
            order_id, "CMD-000001", uuid4(), 5, "Mesa Terraza",
            now, now,
            uuid4(), "Pizza", 1, None, "pending", now,
        ),
        (
            order_id, "CMD-000001", uuid4(), 5, "Mesa Terraza",
            now, now,
            uuid4(), "Coca-Cola", 2, "Sin hielo", "preparing", now,
        ),
    ]
    db = _SelectDb(rows)

    result = t.kds_list_orders(request=_request(), db=db)

    assert len(result) == 1
    grp = result[0]
    assert grp["order_number"] == "CMD-000001"
    assert grp["table_number"] == 5
    assert len(grp["items"]) == 2
    statuses = [i["status"] for i in grp["items"]]
    assert statuses == ["pending", "preparing"]


def test_kds_mark_ready_sets_status_and_ready_at(t):
    item_id = str(uuid4())
    order_id = uuid4()
    db = _SelectDb([(item_id, order_id, "preparing")])

    res = t.kds_mark_ready(item_id, request=_request(), db=db)

    assert res["status"] == "ready"
    assert res["order_id"] == str(order_id)
    assert db.committed is True
    assert len(db.mutations) == 1
    sql, params = db.mutations[0]
    assert "ready_at" in sql
    assert params["st"] == "ready"
    assert "now" in params


def test_kds_mark_served_sets_status_only(t):
    item_id = str(uuid4())
    order_id = uuid4()
    db = _SelectDb([(item_id, order_id, "ready")])

    res = t.kds_mark_served(item_id, request=_request(), db=db)

    assert res["status"] == "served"
    assert db.committed is True
    sql, params = db.mutations[0]
    assert params["st"] == "served"
    assert "ready_at" not in sql


def test_kds_mark_ready_404_when_item_missing(t):
    db = _SelectDb([])
    with pytest.raises(HTTPException) as exc:
        t.kds_mark_ready(str(uuid4()), request=_request(), db=db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "item_not_found"


def test_full_lifecycle_pending_preparing_ready_served(t):
    """Recorre el ciclo de vida llamando los endpoints en orden."""
    item_id = str(uuid4())
    order_id = uuid4()

    db1 = _SelectDb([(item_id, order_id, "preparing")])
    r1 = t.kds_mark_ready(item_id, request=_request(), db=db1)
    assert r1["status"] == "ready"

    db2 = _SelectDb([(item_id, order_id, "ready")])
    r2 = t.kds_mark_served(item_id, request=_request(), db=db2)
    assert r2["status"] == "served"
