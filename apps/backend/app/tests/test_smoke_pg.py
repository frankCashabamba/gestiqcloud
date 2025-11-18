from __future__ import annotations

import uuid as _uuid

import pytest
from sqlalchemy.orm import Session


def test_smoke_sales_order_confirm_creates_reserve(db: Session, tenant_minimal):
    from sqlalchemy import text

    from app.models.inventory.stock import StockMove
    from app.modules.ventas.interface.http.tenant import ConfirmIn, confirm_order

    # Skip on non-Postgres (uses SET LOCAL/policy and UUID bindings)
    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific smoke test")

    tid_str = tenant_minimal["tenant_id_str"]

    # Set RLS context to persist across transactions
    db.execute(text("SET app.tenant_id = :tid"), {"tid": tid_str})

    # Create a product first
    product_id = _uuid.uuid4()
    try:
        db.execute(
            text(
                "INSERT INTO products (id, tenant_id, name, sku) " "VALUES (:id, :tid, :name, :sku)"
            ),
            {
                "id": product_id,
                "tid": tenant_minimal["tenant_id"],
                "name": "Test Product",
                "sku": "TEST-001",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    # Create a sales order with one item for that tenant
    # Use raw SQL since the ORM model doesn't have 'number' field but DB requires it
    tid = tenant_minimal["tenant_id"]
    result = db.execute(
        text(
            "INSERT INTO sales_orders (tenant_id, number, customer_id, status, order_date) "
            "VALUES (:tid, :number, :cid, 'draft', NOW()) RETURNING id"
        ),
        {"tid": tid, "number": f"SO-{tid.hex[:8]}", "cid": None},
    )
    so_id = result.scalar()
    db.commit()

    # Add order items (product_id must exist in products table)
    db.execute(
        text(
            "INSERT INTO sales_order_items (sales_order_id, product_id, quantity, unit_price, line_total) "
            "VALUES (:order_id, :product_id, :qty, :price, :total)"
        ),
        {
            "order_id": so_id,
            "product_id": product_id,
            "qty": 2,
            "price": 10,
            "total": 20,
        },
    )
    db.commit()

    # Create a minimal SalesOrder object for the confirm_order call
    class _SalesOrder:
        id = so_id
        status = "draft"

    so = _SalesOrder()

    # Build a minimal request with access_claims
    class _State:
        access_claims = {"tenant_id": tid_str, "user_id": "tester"}

    class _Req:
        state = _State()

    # Create a warehouse first
    warehouse_id = _uuid.uuid4()
    try:
        db.execute(
            text(
                "INSERT INTO warehouses (id, tenant_id, name, active) "
                "VALUES (:id, :tid, :name, TRUE)"
            ),
            {"id": warehouse_id, "tid": tid, "name": "Test Warehouse"},
        )
        db.commit()
    except Exception:
        db.rollback()

    # Act: confirm the order to create reserve stock moves
    res = confirm_order(so.id, ConfirmIn(warehouse_id=str(warehouse_id)), _Req(), db)
    assert res.status == "confirmed"

    # Assert: there is at least one tentative reserve move for this tenant/order
    mv = (
        db.query(StockMove)
        .filter(
            StockMove.tenant_id == tid_str,
            StockMove.ref_type == "sales_order",
            StockMove.ref_id == str(so.id),
        )
        .first()
    )
    assert mv is not None
    assert mv.kind == "reserve"
    assert mv.tentative is True
