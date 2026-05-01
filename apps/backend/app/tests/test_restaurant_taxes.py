"""Tests: `_recalculate_order_totals` calcula tax_total por producto."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _RecordingDb:
    """Devuelve filas de SELECT y captura el UPDATE final con sus params."""

    def __init__(self, rows):
        self._rows = rows
        self.update_params: dict | None = None
        self.update_sql: str | None = None

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if sql.lstrip().upper().startswith("SELECT"):
            return _FakeResult(self._rows)
        self.update_sql = sql
        self.update_params = dict(params or {})
        return _FakeResult([])


def test_tax_total_uses_product_tax_rate(monkeypatch):
    from app.modules.restaurant.interface.http import tenant as t

    tenant_id = uuid4()
    rows = [
        (Decimal("100.00"), Decimal("21.00"), tenant_id),
        (Decimal("50.00"), Decimal("10.00"), tenant_id),
    ]
    db = _RecordingDb(rows)

    def _boom(*a, **kw):
        raise AssertionError("default tenant tax should not be queried")

    monkeypatch.setattr(
        "app.modules.shared.services.tax.resolve_tenant_default_tax_rate", _boom
    )

    result = t._recalculate_order_totals(db, str(uuid4()))

    assert result["subtotal"] == 150.0
    assert result["tax_total"] == 26.0
    assert result["total"] == 176.0
    assert db.update_params is not None
    assert db.update_params["tax_total"] == 26.0
    assert db.update_params["subtotal"] == 150.0
    assert db.update_params["total"] == 176.0


def test_tax_total_falls_back_to_tenant_default(monkeypatch):
    from app.modules.restaurant.interface.http import tenant as t

    tenant_id = uuid4()
    rows = [(Decimal("200.00"), None, tenant_id)]
    db = _RecordingDb(rows)

    monkeypatch.setattr(
        "app.modules.shared.services.tax.resolve_tenant_default_tax_rate",
        lambda db, tid, **kw: Decimal("0.21"),
    )

    result = t._recalculate_order_totals(db, str(uuid4()))

    assert result["subtotal"] == 200.0
    assert result["tax_total"] == 42.0
    assert result["total"] == 242.0


def test_tax_total_zero_when_no_items():
    from app.modules.restaurant.interface.http import tenant as t

    db = _RecordingDb([])
    result = t._recalculate_order_totals(db, str(uuid4()))
    assert result == {"subtotal": 0.0, "tax_total": 0.0, "total": 0.0}
