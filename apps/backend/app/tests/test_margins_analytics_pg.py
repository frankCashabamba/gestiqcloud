from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_margins_endpoints_return_snapshot(db: Session, tenant_minimal, superuser_factory):
    from app.models.company.company_user import CompanyUser
    from app.modules.pos.interface.http.tenant import (
        CheckoutIn,
        OpenShiftIn,
        ReceiptCreateIn,
        ReceiptLineIn,
        RegisterIn,
        checkout,
        create_receipt,
        create_register,
        margins_by_customer,
        margins_by_product,
        margins_product_lines,
        open_shift,
    )

    tid = tenant_minimal["tenant_id"]
    tid_str = tenant_minimal["tenant_id_str"]

    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific test (RLS + SET LOCAL)")

    db.execute(text(f"SET app.tenant_id = '{tid_str}'"))
    db.execute(text("SET session_replication_role = REPLICA"))

    user = superuser_factory(username="pos_margins_tester", tenant_id=tid)
    company_user = db.query(CompanyUser).filter(CompanyUser.id == user.id).first()
    if not company_user:
        company_user = CompanyUser(
            id=user.id,
            tenant_id=tid,
            first_name="POS",
            last_name="Tester",
            email=f"{user.username}@example.com",
            username=user.username,
            is_active=True,
            is_company_admin=True,
            password_hash=user.password_hash,
            is_verified=True,
        )
        db.add(company_user)
        db.commit()
    elif company_user.tenant_id != tid:
        company_user.tenant_id = tid
        company_user.is_active = True
        company_user.is_company_admin = True
        db.commit()

    class _State:
        access_claims = {"tenant_id": tid_str, "user_id": str(company_user.id)}

    class _Req:
        state = _State()

    product_id = _uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO products (id, tenant_id, name, sku, active, stock, unit) "
            "VALUES (:id, :tid, :name, :sku, TRUE, 0, 'unit')"
        ),
        {"id": product_id, "tid": tid, "name": "Margins Product", "sku": "M-001"},
    )

    warehouse_id = _uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO warehouses (id, tenant_id, code, name, active) "
            "VALUES (:id, :tid, :code, :name, TRUE)"
        ),
        {"id": warehouse_id, "tid": tid, "code": "WH-MARG", "name": "Margins WH"},
    )
    db.commit()

    reg = create_register(
        RegisterIn(code="R-M", name="Caja Margen", default_warehouse_id=str(warehouse_id)),
        _Req(),
        db,
    )
    sh = open_shift(OpenShiftIn(register_id=str(reg["id"]), opening_float=50.0), _Req(), db)

    db.execute(
        text(
            "INSERT INTO stock_items(id, tenant_id, warehouse_id, product_id, qty) "
            "VALUES (gen_random_uuid(), :tid, :wid, :pid, :qty)"
        ),
        {"tid": tid, "wid": warehouse_id, "pid": product_id, "qty": 10},
    )
    db.execute(
        text(
            "INSERT INTO inventory_cost_state("
            "tenant_id, warehouse_id, product_id, on_hand_qty, avg_cost"
            ") VALUES (:tid, :wid, :pid, :qty, :avg)"
        ),
        {"tid": tid, "wid": warehouse_id, "pid": product_id, "qty": 10, "avg": 3.0},
    )
    db.commit()

    rc = create_receipt(
        ReceiptCreateIn(
            shift_id=sh["id"],
            register_id=str(reg["id"]),
            lines=[ReceiptLineIn(product_id=str(product_id), qty=2, unit_price=8.0)],
        ),
        _Req(),
        db,
    )

    checkout(
        rc["id"],
        CheckoutIn(payments=[{"method": "cash", "amount": 16.0}], warehouse_id=str(warehouse_id)),
        _Req(),
        db,
    )

    from_date = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    to_date = (datetime.utcnow() + timedelta(days=1)).date().isoformat()

    prod_rows = margins_by_product(
        _Req(),
        db,
        from_date=from_date,
        to_date=to_date,
        warehouse_id=str(warehouse_id),
        limit=10,
    )
    assert prod_rows
    assert prod_rows[0]["product_id"] == str(product_id)
    assert prod_rows[0]["sales_net"] == 16.0
    assert prod_rows[0]["cogs"] == 6.0
    assert prod_rows[0]["gross_profit"] == 10.0

    cust_rows = margins_by_customer(
        _Req(),
        db,
        from_date=from_date,
        to_date=to_date,
        warehouse_id=str(warehouse_id),
        limit=10,
    )
    assert cust_rows
    assert cust_rows[0]["sales_net"] == 16.0

    line_rows = margins_product_lines(
        str(product_id),
        _Req(),
        db,
        from_date=from_date,
        to_date=to_date,
        warehouse_id=str(warehouse_id),
        limit=10,
    )
    assert line_rows
    assert line_rows[0]["net_total"] == 16.0
