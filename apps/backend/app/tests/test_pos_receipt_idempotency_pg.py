from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.pos.register import POSRegister, POSShift
from app.modules.pos.interface.http._deps import ReceiptCreateIn, ReceiptLineIn
from app.modules.pos.interface.http.receipts import create_receipt


def _req(tenant_id: str, user_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(access_claims={"tenant_id": tenant_id, "user_id": user_id})
    )


def test_create_receipt_is_idempotent_by_client_request_id(
    db: Session, tenant_minimal
):
    eng = db.get_bind()
    if eng.dialect.name != "postgresql":
        pytest.skip("Postgres-specific idempotency test")

    tenant_id = tenant_minimal["tenant_id"]
    tenant_id_str = tenant_minimal["tenant_id_str"]
    user_id = str(uuid.uuid4())

    db.execute(text(f"SET app.tenant_id = '{tenant_id_str}'"))
    db.execute(text("SET session_replication_role = REPLICA"))

    product_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO products (id, tenant_id, name, sku, active, stock, unit) "
            "VALUES (:id, :tid, :name, :sku, TRUE, 0, 'unit')"
        ),
        {
            "id": product_id,
            "tid": tenant_id,
            "name": "Idempotent POS Product",
            "sku": f"POS-IDEMP-{product_id.hex[:8]}",
        },
    )

    register = POSRegister(id=uuid.uuid4(), tenant_id=tenant_id, name="Caja Idempotente", active=True)
    shift = POSShift(
        id=uuid.uuid4(),
        register_id=register.id,
        opened_by=uuid.uuid4(),
        opening_float=0,
        status="open",
    )
    db.add_all([register, shift])
    db.commit()

    payload = ReceiptCreateIn(
        shift_id=str(shift.id),
        register_id=str(register.id),
        client_request_id="offline-retry-001",
        lines=[
            ReceiptLineIn(
                product_id=str(product_id),
                qty=1,
                unit_price=1.65,
            )
        ],
    )
    request = _req(tenant_id_str, user_id)

    first = create_receipt(payload, request, db)
    second = create_receipt(payload, request, db)

    assert first["id"] == second["id"]
    assert second["idempotent_replay"] is True

    receipt_count = db.execute(
        text(
            "SELECT COUNT(*) FROM pos_receipts "
            "WHERE tenant_id = :tid AND client_request_id = :client_request_id"
        ),
        {"tid": tenant_id, "client_request_id": "offline-retry-001"},
    ).scalar()
    assert int(receipt_count or 0) == 1

    line_count = db.execute(
        text(
            "SELECT COUNT(*) "
            "FROM pos_receipt_lines rl "
            "JOIN pos_receipts r ON r.id = rl.receipt_id "
            "WHERE r.tenant_id = :tid AND r.client_request_id = :client_request_id"
        ),
        {"tid": tenant_id, "client_request_id": "offline-retry-001"},
    ).scalar()
    assert int(line_count or 0) == 1
