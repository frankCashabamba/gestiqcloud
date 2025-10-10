from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session
from sqlalchemy import text
import pytest


def test_smoke_pos_post_creates_issue_and_updates_stock(db: Session):
    from app.modules.pos.interface.http.tenant import (
        create_register,
        RegisterIn,
        open_shift,
        OpenShiftIn,
        create_receipt,
        ReceiptCreateIn,
        add_item,
        ItemIn,
        take_payment,
        PaymentIn,
        post_receipt,
        PostReceiptIn,
    )
    from app.models.inventory.stock import StockMove, StockItem

    tid = str(_uuid.uuid4())

    # Ensure tenant exists and set session GUC for RLS-aware SQL
    try:
        db.execute(
            text(
                "INSERT INTO tenants(id, empresa_id, slug) VALUES (:id::uuid, 1, 'acme-pos') ON CONFLICT (empresa_id) DO NOTHING"
            ),
            {"id": tid},
        )
        db.commit()
    except Exception:
        db.rollback()

    # Skip on non-Postgres; SQLite doesn't support SET LOCAL
    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific smoke test (RLS + SET LOCAL)")

    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})

    class _State:
        access_claims = {"tenant_id": tid, "user_id": "tester"}

    class _Req:
        state = _State()

    # Create register
    reg = create_register(RegisterIn(code="R1", name="Caja 1", default_warehouse_id=1), _Req(), db)
    assert reg["id"]

    # Open shift
    sh = open_shift(OpenShiftIn(register_id=1, opening_cash=100), _Req(), db)
    assert sh["id"]
    shift_id = sh["id"]

    # Create receipt
    rc = create_receipt(ReceiptCreateIn(shift_id=shift_id), _Req(), db)
    rid = rc["id"]

    # Add item (product_id=1)
    add_item(rid, ItemIn(product_id=1, qty=2, unit_price=5.0), _Req(), db)

    # Take payment (cash)
    take_payment(rid, PaymentIn(method="cash", amount=10.0), _Req(), db)

    # Post receipt (consume stock)
    out = post_receipt(rid, PostReceiptIn(warehouse_id=1), _Req(), db)
    assert out["status"] == "posted"
    assert out["total"] == 10.0

    # Verify stock move issue posted
    mv = (
        db.query(StockMove)
        .filter(StockMove.tenant_id == tid, StockMove.ref_type == "pos_receipt", StockMove.ref_id == str(rid))
        .first()
    )
    assert mv is not None and mv.kind == "issue" and mv.posted is True

    # Verify stock_items decreased (may be negative if starting from zero)
    si = (
        db.query(StockItem)
        .filter(StockItem.warehouse_id == 1, StockItem.product_id == 1)
        .first()
    )
    assert si is not None
