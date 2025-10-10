from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session
import uuid as _uuid
import pytest


def test_smoke_sales_order_confirm_creates_reserve(db: Session):
    from sqlalchemy import text
    from app.models.sales.order import SalesOrder, SalesOrderItem
    from app.models.inventory.stock import StockMove
    from app.modules.ventas.interface.http.tenant import confirm_order, ConfirmIn

    # Skip on non-Postgres (uses SET LOCAL/policy and UUID bindings)
    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific smoke test")

    # Arrange: ensure tenants table has a row mapping empresa_id 1 to a UUID
    tid = _uuid.uuid4()
    try:
        db.execute(
            text(
                "INSERT INTO tenants(id, empresa_id, slug) VALUES (:id::uuid, 1, 'acme') ON CONFLICT (empresa_id) DO NOTHING"
            ),
            {"id": str(tid)},
        )
        db.commit()
    except Exception:
        db.rollback()

    # Create a sales order with one item for that tenant
    so = SalesOrder(tenant_id=tid, customer_id=None, status="draft")
    db.add(so)
    db.flush()
    db.add(SalesOrderItem(tenant_id=tid, order_id=so.id, product_id=1, qty=2, unit_price=10))
    db.commit()

    # Build a minimal request with access_claims
    class _State:
        access_claims = {"tenant_id": str(tid), "user_id": "tester"}

    class _Req:
        state = _State()

    # Act: confirm the order to create reserve stock moves
    res = confirm_order(so.id, ConfirmIn(warehouse_id=1), _Req(), db)
    assert res.status == "confirmed"

    # Assert: there is at least one tentative reserve move for this tenant/order
    mv = (
        db.query(StockMove)
        .filter(StockMove.tenant_id == str(tid), StockMove.ref_type == "sales_order", StockMove.ref_id == str(so.id))
        .first()
    )
    assert mv is not None
    assert mv.kind == "reserve"
    assert mv.tentative is True
