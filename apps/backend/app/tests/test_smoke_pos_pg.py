from __future__ import annotations

import uuid as _uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_smoke_pos_post_creates_issue_and_updates_stock(
    db: Session, tenant_minimal, superuser_factory
):
    from app.models.inventory.stock import StockItem, StockMove
    from app.modules.pos.interface.http.tenant import (
        CheckoutIn,
        OpenShiftIn,
        RefundReceiptIn,
        ReceiptCreateIn,
        ReceiptLineIn,
        RegisterIn,
        checkout,
        create_receipt,
        create_register,
        open_shift,
        refund_receipt,
    )

    tid = tenant_minimal["tenant_id"]
    tid_str = tenant_minimal["tenant_id_str"]

    # Skip on non-Postgres; SQLite doesn't support SET LOCAL
    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific smoke test (RLS + SET LOCAL)")

    # Use SET (not SET LOCAL) to persist RLS context across multiple transactions
    db.execute(text(f"SET app.tenant_id = '{tid_str}'"))

    # Disable RLS constraints to allow direct INSERT without row visibility issues
    db.execute(text("SET session_replication_role = REPLICA"))

    # Create a valid superuser for the test
    user = superuser_factory(username="pos_tester")

    class _State:
        access_claims = {"tenant_id": tid_str, "user_id": str(user.id)}

    class _Req:
        state = _State()

    # Create a product first
    product_id = _uuid.uuid4()
    try:
        db.execute(
            text(
                "INSERT INTO products (id, tenant_id, name, sku) " "VALUES (:id, :tid, :name, :sku)"
            ),
            {
                "id": product_id,
                "tid": tid,
                "name": "POS Product",
                "sku": "POS-001",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    # Create warehouse first
    warehouse_id = _uuid.uuid4()
    warehouse_code = f"POS-WH-{warehouse_id.hex[:8]}"
    try:
        db.execute(
            text(
                "INSERT INTO warehouses (id, tenant_id, code, name, active) "
                "VALUES (:id, :tid, :code, :name, TRUE)"
            ),
            {"id": warehouse_id, "tid": tid, "code": warehouse_code, "name": "Test Warehouse"},
        )
        db.commit()
    except Exception:
        db.rollback()

    # Create register
    reg = create_register(
        RegisterIn(code="R1", name="Caja 1", default_warehouse_id=str(warehouse_id)), _Req(), db
    )
    assert reg["id"]

    # Open shift (register_id must be string, opening_float is required)
    sh = open_shift(OpenShiftIn(register_id=str(reg["id"]), opening_float=100.0), _Req(), db)
    assert sh["id"]
    shift_id = sh["id"]

    # Seed stock and cost state
    try:
        db.execute(
            text(
                "INSERT INTO stock_items(id, tenant_id, warehouse_id, product_id, qty) "
                "VALUES (gen_random_uuid(), :tid, :wid, :pid, :qty)"
            ),
            {"tid": tid, "wid": warehouse_id, "pid": product_id, "qty": 5},
        )
        db.execute(
            text(
                "INSERT INTO inventory_cost_state("
                "tenant_id, warehouse_id, product_id, on_hand_qty, avg_cost"
                ") VALUES (:tid, :wid, :pid, :qty, :avg)"
            ),
            {"tid": tid, "wid": warehouse_id, "pid": product_id, "qty": 5, "avg": 2.5},
        )
        db.commit()
    except Exception:
        db.rollback()

    # Create receipt with one line
    rc = create_receipt(
        ReceiptCreateIn(
            shift_id=shift_id,
            register_id=str(reg["id"]),
            lines=[
                ReceiptLineIn(
                    product_id=str(product_id),
                    qty=2,
                    unit_price=5.0,
                )
            ],
        ),
        _Req(),
        db,
    )
    rid = rc["id"]

    # Checkout receipt (consume stock + margins)
    out = checkout(
        rid,
        CheckoutIn(payments=[{"method": "cash", "amount": 10.0}], warehouse_id=str(warehouse_id)),
        _Req(),
        db,
    )
    assert out["status"] == "paid"
    assert out["totals"]["total"] == 10.0

    # Verify stock move issue posted
    mv = (
        db.query(StockMove)
        .filter(
            StockMove.tenant_id == tid_str,
            StockMove.ref_type == "pos_receipt",
            StockMove.ref_id == str(rid),
        )
        .first()
    )
    assert mv is not None and mv.kind == "sale" and mv.posted is True
    assert float(mv.unit_cost or 0) == 2.5
    assert float(mv.total_cost or 0) == 5.0

    # Verify stock_items decreased
    si = (
        db.query(StockItem)
        .filter(
            StockItem.warehouse_id == str(warehouse_id), StockItem.product_id == str(product_id)
        )
        .first()
    )
    assert si is not None
    assert float(si.qty or 0) == 3.0

    state = db.execute(
        text(
            "SELECT on_hand_qty, avg_cost FROM inventory_cost_state "
            "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
        ),
        {"tid": tid, "wid": warehouse_id, "pid": product_id},
    ).first()
    assert state is not None
    assert float(state[0] or 0) == 3.0
    assert float(state[1] or 0) == 2.5

    refund = refund_receipt(
        rid,
        RefundReceiptIn(reason="test refund"),
        _Req(),
        db,
    )
    assert refund["status"] == "refunded"

    si = (
        db.query(StockItem)
        .filter(
            StockItem.warehouse_id == str(warehouse_id), StockItem.product_id == str(product_id)
        )
        .first()
    )
    assert float(si.qty or 0) == 5.0

    refund_line = db.execute(
        text(
            "SELECT COUNT(*) FROM pos_receipt_lines WHERE receipt_id = :rid AND qty < 0"
        ),
        {"rid": rid},
    ).scalar()
    assert int(refund_line or 0) == 1

    # Verify margin snapshot
    line = db.execute(
        text(
            "SELECT net_total, cogs_unit, cogs_total, gross_profit, gross_margin_pct "
            "FROM pos_receipt_lines WHERE receipt_id = :rid"
        ),
        {"rid": rid},
    ).first()
    assert line is not None
    assert float(line[0] or 0) == 10.0
    assert float(line[1] or 0) == 2.5
    assert float(line[2] or 0) == 5.0
    assert float(line[3] or 0) == 5.0
    assert float(line[4] or 0) == 0.5
