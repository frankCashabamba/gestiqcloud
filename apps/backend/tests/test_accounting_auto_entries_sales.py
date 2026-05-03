"""Tests del hook contable automático SALES (post_sale_entry).

Verifica:
- Se crea un asiento POSTED con Cuentas por Cobrar (1.1.02) al confirmar.
- Si el total es 0 no se crea asiento.
- Si las cuentas por defecto NO existen → log warning + skip (devuelve None).
- Idempotencia: invocar dos veces revierte el primero (CANCELLED) y crea uno nuevo.
- paid=True usa Caja (1.1.01) en vez de Cuentas por Cobrar.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal


from app.models.accounting.chart_of_accounts import ChartOfAccounts
from app.models.sales.order import SalesOrder
from app.modules.sales.application.journal import (
    CODE_AR,
    CODE_CASH,
    CODE_SALES,
    CODE_VAT_OUTPUT,
    post_sale_entry,
)


def _seed_accounts(db, tenant_id, codes):
    accounts = {}
    for code, type_ in codes:
        acc = ChartOfAccounts(
            tenant_id=tenant_id,
            code=code,
            name=f"Cuenta {code}",
            type=type_,
            level=4,
            can_post=True,
            active=True,
            debit_balance=Decimal("0"),
            credit_balance=Decimal("0"),
            balance=Decimal("0"),
        )
        db.add(acc)
        accounts[code] = acc
    db.flush()
    return accounts


def _make_sale(db, tenant_id, *, total="120", subtotal="100", tax="20"):
    order = SalesOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        number=f"SO-{uuid.uuid4().hex[:6]}",
        order_date=date.today(),
        subtotal=Decimal(subtotal),
        tax=Decimal(tax),
        total=Decimal(total),
        status="draft",
    )
    db.add(order)
    db.flush()
    return order


def test_post_sale_entry_creates_balanced_posted_entry(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    _seed_accounts(
        db,
        tenant_id,
        [(CODE_AR, "ASSET"), (CODE_SALES, "INCOME"), (CODE_VAT_OUTPUT, "LIABILITY")],
    )
    sale = _make_sale(db, tenant_id)

    entry = post_sale_entry(db, sale, user_id=None, paid=False)

    assert entry is not None
    assert entry.status == "POSTED"
    assert entry.ref_doc_type == "sales_order"
    assert entry.ref_doc_id == sale.id
    assert entry.debit_total == entry.credit_total
    assert entry.number.startswith("ASI-")


def test_post_sale_entry_skips_when_default_accounts_missing(db, tenant_minimal, caplog):
    tenant_id = tenant_minimal["tenant_id"]
    sale = _make_sale(db, tenant_id)

    with caplog.at_level("WARNING"):
        result = post_sale_entry(db, sale, user_id=None, paid=False)

    assert result is None
    assert any("cuentas por defecto faltantes" in rec.message for rec in caplog.records)


def test_post_sale_entry_idempotent_reverses_previous(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    _seed_accounts(
        db,
        tenant_id,
        [(CODE_AR, "ASSET"), (CODE_SALES, "INCOME"), (CODE_VAT_OUTPUT, "LIABILITY")],
    )
    sale = _make_sale(db, tenant_id)

    e1 = post_sale_entry(db, sale, user_id=None, paid=False)
    e2 = post_sale_entry(db, sale, user_id=None, paid=False)
    assert e1 is not None and e2 is not None
    assert e1.id != e2.id
    db.refresh(e1)
    assert e1.status == "CANCELLED"
    assert e2.status == "POSTED"


def test_post_sale_entry_paid_uses_cash_account(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    accs = _seed_accounts(
        db,
        tenant_id,
        [
            (CODE_AR, "ASSET"),
            (CODE_CASH, "ASSET"),
            (CODE_SALES, "INCOME"),
            (CODE_VAT_OUTPUT, "LIABILITY"),
        ],
    )
    sale = _make_sale(db, tenant_id)

    entry = post_sale_entry(db, sale, user_id=None, paid=True)
    assert entry is not None
    debit_account_ids = {l.account_id for l in entry.lines if l.debit > 0}
    assert accs[CODE_CASH].id in debit_account_ids
    assert accs[CODE_AR].id not in debit_account_ids


def test_post_sale_entry_zero_total_returns_none(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    sale = _make_sale(db, tenant_id, total="0", subtotal="0", tax="0")
    assert post_sale_entry(db, sale, user_id=None) is None
