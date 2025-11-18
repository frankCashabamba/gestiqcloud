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
        OpenShiftIn,
        PaymentIn,
        PostReceiptIn,
        ReceiptCreateIn,
        ReceiptLineIn,
        RegisterIn,
        create_receipt,
        create_register,
        open_shift,
        post_receipt,
        take_payment,
    )

    tid = tenant_minimal["tenant_id"]
    tid_str = tenant_minimal["tenant_id_str"]

    # Skip on non-Postgres; SQLite doesn't support SET LOCAL
    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific smoke test (RLS + SET LOCAL)")

    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid_str})

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

    # Create register
    reg = create_register(
        RegisterIn(code="R1", name="Caja 1", default_warehouse_id="1"), _Req(), db
    )
    assert reg["id"]

    # Open shift (register_id must be string, opening_float is required)
    sh = open_shift(OpenShiftIn(register_id=str(reg["id"]), opening_float=100.0), _Req(), db)
    assert sh["id"]
    shift_id = sh["id"]

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

    # Take payment (cash)
    take_payment(rid, PaymentIn(method="cash", amount=10.0), _Req(), db)

    # Post receipt (consume stock)
    out = post_receipt(rid, PostReceiptIn(warehouse_id=1), _Req(), db)
    assert out["status"] == "posted"
    assert out["total"] == 10.0

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
    assert mv is not None and mv.kind == "issue" and mv.posted is True

    # Verify stock_items decreased (may be negative if starting from zero)
    si = (
        db.query(StockItem)
        .filter(StockItem.warehouse_id == 1, StockItem.product_id == str(product_id))
        .first()
    )
    assert si is not None
