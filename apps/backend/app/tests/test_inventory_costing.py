from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_inventory_costing_wac(db: Session, tenant_minimal):
    from app.services.inventory_costing import InventoryCostingService

    tid = tenant_minimal["tenant_id"]
    tid_str = tenant_minimal["tenant_id_str"]

    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific test (RLS + SET LOCAL)")

    db.execute(text(f"SET app.tenant_id = '{tid_str}'"))
    db.execute(text("SET session_replication_role = REPLICA"))

    wh_id = db.execute(text("SELECT gen_random_uuid()")).scalar()
    prod_id = db.execute(text("SELECT gen_random_uuid()")).scalar()

    db.execute(
        text(
            "INSERT INTO warehouses (id, tenant_id, code, name, active) "
            "VALUES (:id, :tid, :code, :name, TRUE)"
        ),
        {"id": wh_id, "tid": tid, "code": "WAC-WH", "name": "WAC WH"},
    )
    db.execute(
        text(
            "INSERT INTO products (id, tenant_id, name, active, stock, unit) "
            "VALUES (:id, :tid, :name, TRUE, 0, 'unit')"
        ),
        {"id": prod_id, "tid": tid, "name": "WAC Product"},
    )
    db.commit()

    svc = InventoryCostingService(db)
    svc.apply_inbound(
        str(tid),
        str(wh_id),
        str(prod_id),
        qty=Decimal("10"),
        unit_cost=Decimal("2.50"),
        initial_qty=Decimal("0"),
        initial_avg_cost=Decimal("0"),
    )
    svc.apply_inbound(
        str(tid),
        str(wh_id),
        str(prod_id),
        qty=Decimal("10"),
        unit_cost=Decimal("3.00"),
        initial_qty=Decimal("10"),
        initial_avg_cost=Decimal("2.50"),
    )
    svc.apply_outbound(
        str(tid),
        str(wh_id),
        str(prod_id),
        qty=Decimal("5"),
        allow_negative=False,
        initial_qty=Decimal("20"),
        initial_avg_cost=Decimal("2.75"),
    )
    db.commit()

    row = db.execute(
        text(
            "SELECT on_hand_qty, avg_cost FROM inventory_cost_state "
            "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
        ),
        {"tid": tid, "wid": wh_id, "pid": prod_id},
    ).first()

    assert row is not None
    assert float(row[0] or 0) == 15.0
    assert float(row[1] or 0) == 2.75
