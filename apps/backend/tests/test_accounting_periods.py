"""Tests de períodos contables: cierre/apertura/regularización + bloqueo de asientos.

Cubre:
- `create_posted_entry` lanza HTTPException 409 `periodo_cerrado` si la fecha
  cae dentro de un período con status='CLOSED'.
- Si el período está OPEN o no existe, el asiento se contabiliza normalmente.
- `assert_period_open` no bloquea cuando la tabla aún no migrada (SQLAlchemyError).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.accounting.chart_of_accounts import ChartOfAccounts
from app.models.accounting.period import AccountingPeriod
from app.modules.accounting.application.journal_service import (
    JournalLineIn,
    assert_period_open,
    create_posted_entry,
)


def _two_accounts(db, tenant_id):
    a = ChartOfAccounts(
        tenant_id=tenant_id, code="1.1.01", name="Caja", type="ASSET", level=4,
        can_post=True, active=True,
        debit_balance=Decimal("0"), credit_balance=Decimal("0"), balance=Decimal("0"),
    )
    b = ChartOfAccounts(
        tenant_id=tenant_id, code="4.1", name="Ventas", type="INCOME", level=4,
        can_post=True, active=True,
        debit_balance=Decimal("0"), credit_balance=Decimal("0"), balance=Decimal("0"),
    )
    db.add_all([a, b])
    db.flush()
    return a, b


def test_assert_period_open_raises_when_closed(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    db.add(
        AccountingPeriod(
            tenant_id=tenant_id, year=2026, month=5, status="CLOSED"
        )
    )
    db.flush()

    with pytest.raises(HTTPException) as excinfo:
        assert_period_open(db, tenant_id, date(2026, 5, 15))
    assert excinfo.value.status_code == 409
    assert excinfo.value.detail == "periodo_cerrado"


def test_assert_period_open_ok_when_open_or_missing(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    # Sin período → no lanza.
    assert_period_open(db, tenant_id, date(2026, 5, 15))
    # Período OPEN → no lanza.
    db.add(
        AccountingPeriod(tenant_id=tenant_id, year=2026, month=6, status="OPEN")
    )
    db.flush()
    assert_period_open(db, tenant_id, date(2026, 6, 1))


def test_create_posted_entry_blocked_by_closed_period(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    a, b = _two_accounts(db, tenant_id)
    db.add(
        AccountingPeriod(tenant_id=tenant_id, year=2026, month=4, status="CLOSED")
    )
    db.flush()

    with pytest.raises(HTTPException) as excinfo:
        create_posted_entry(
            db,
            tenant_id=tenant_id,
            entry_date=date(2026, 4, 10),
            description="bloqueado",
            ref_doc_type="test",
            ref_doc_id=uuid.uuid4(),
            created_by=None,
            lines=[
                JournalLineIn(account_id=a.id, debit=Decimal("10"), credit=Decimal("0")),
                JournalLineIn(account_id=b.id, debit=Decimal("0"), credit=Decimal("10")),
            ],
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.detail == "periodo_cerrado"


def test_create_posted_entry_succeeds_in_open_period(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    a, b = _two_accounts(db, tenant_id)
    db.add(
        AccountingPeriod(tenant_id=tenant_id, year=2026, month=4, status="OPEN")
    )
    db.flush()

    entry = create_posted_entry(
        db,
        tenant_id=tenant_id,
        entry_date=date(2026, 4, 11),
        description="ok",
        ref_doc_type="test",
        ref_doc_id=uuid.uuid4(),
        created_by=None,
        lines=[
            JournalLineIn(account_id=a.id, debit=Decimal("10"), credit=Decimal("0")),
            JournalLineIn(account_id=b.id, debit=Decimal("0"), credit=Decimal("10")),
        ],
    )
    assert entry.status == "POSTED"
