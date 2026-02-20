from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.models.pos.receipt import POSReceipt
from app.models.pos.register import POSRegister, POSShift
from app.models.tenant import Tenant
from app.modules.company.interface.http.admin import (
    admin_backfill_pos_receipt_documents,
    admin_list_pos_backfill_candidates,
)
from app.modules.pos.interface.http.tenant import backfill_receipt_documents


def _req(tenant_id: uuid.UUID | None = None) -> SimpleNamespace:
    claims: dict[str, str] = {"user_id": str(uuid.uuid4())}
    if tenant_id is not None:
        claims["tenant_id"] = str(tenant_id)
    return SimpleNamespace(state=SimpleNamespace(access_claims=claims))


def _create_paid_receipt(db, tenant_id: uuid.UUID, number: str) -> uuid.UUID:
    register = POSRegister(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=f"Reg-{number}",
        active=True,
    )
    db.add(register)
    db.flush()

    shift = POSShift(
        id=uuid.uuid4(),
        register_id=register.id,
        opened_by=uuid.uuid4(),
        opened_at=datetime.utcnow(),
        opening_float=0,
        status="open",
    )
    db.add(shift)
    db.flush()

    receipt = POSReceipt(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        register_id=register.id,
        shift_id=shift.id,
        number=number,
        status="paid",
        gross_total=100,
        tax_total=12,
        currency="USD",
        paid_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(receipt)
    db.commit()
    return receipt.id


def test_tenant_backfill_rejects_cross_tenant_receipt(db):
    tenant_a = Tenant(id=uuid.uuid4(), name="A", slug=f"a-{uuid.uuid4().hex[:6]}")
    tenant_b = Tenant(id=uuid.uuid4(), name="B", slug=f"b-{uuid.uuid4().hex[:6]}")
    db.add_all([tenant_a, tenant_b])
    db.commit()

    receipt_a = _create_paid_receipt(db, tenant_a.id, "R-A-001")

    with pytest.raises(HTTPException) as exc:
        backfill_receipt_documents(
            receipt_id=str(receipt_a),
            request=_req(tenant_b.id),
            db=db,
        )

    assert exc.value.status_code == 404
    assert "Recibo no encontrado" in str(exc.value.detail)


def test_admin_backfill_rejects_cross_tenant_receipt(db):
    tenant_a = Tenant(id=uuid.uuid4(), name="A2", slug=f"a2-{uuid.uuid4().hex[:6]}")
    tenant_b = Tenant(id=uuid.uuid4(), name="B2", slug=f"b2-{uuid.uuid4().hex[:6]}")
    db.add_all([tenant_a, tenant_b])
    db.commit()

    receipt_a = _create_paid_receipt(db, tenant_a.id, "R-A2-001")

    with pytest.raises(HTTPException) as exc:
        admin_backfill_pos_receipt_documents(
            tenant_id=str(tenant_b.id),
            receipt_id=str(receipt_a),
            request=_req(),
            db=db,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "receipt_not_found"


def test_admin_backfill_candidates_are_tenant_scoped(db):
    db.execute(
        text(
            "CREATE TABLE IF NOT EXISTS sales_orders ("
            "id TEXT PRIMARY KEY, "
            "tenant_id TEXT, "
            "pos_receipt_id TEXT)"
        )
    )
    db.commit()

    tenant_a = Tenant(id=uuid.uuid4(), name="A3", slug=f"a3-{uuid.uuid4().hex[:6]}")
    tenant_b = Tenant(id=uuid.uuid4(), name="B3", slug=f"b3-{uuid.uuid4().hex[:6]}")
    db.add_all([tenant_a, tenant_b])
    db.commit()

    receipt_a = _create_paid_receipt(db, tenant_a.id, "R-A3-001")
    _create_paid_receipt(db, tenant_b.id, "R-B3-001")

    result = admin_list_pos_backfill_candidates(
        tenant_id=str(tenant_a.id),
        request=_req(),
        db=db,
    )

    assert result["ok"] is True
    ids = {item["receipt_id"] for item in result["items"]}
    assert str(receipt_a) in ids
    assert len(ids) == 1
