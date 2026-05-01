"""Tests del hook contable automático PURCHASES (post_purchase_entry).

Verifica DEBE Inventario/IVA — HABER Cuentas por Pagar, idempotencia y skip
cuando faltan cuentas por defecto.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.models.accounting.chart_of_accounts import ChartOfAccounts
from app.models.purchases.purchase import Purchase
from app.modules.purchases.application.journal import (
    CODE_AP,
    CODE_INVENTORY,
    CODE_VAT_INPUT,
    post_purchase_entry,
)


def _seed_accounts(db, tenant_id, codes):
    out = {}
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
        out[code] = acc
    db.flush()
    return out


def _make_purchase(db, tenant_id, *, total="120", subtotal="100", taxes="20"):
    p = Purchase(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        number=f"PO-{uuid.uuid4().hex[:6]}",
        date=date.today(),
        subtotal=Decimal(subtotal),
        taxes=Decimal(taxes),
        total=Decimal(total),
        status="received",
        user_id=tenant_id,  # placeholder UUID
    )
    db.add(p)
    db.flush()
    return p


def test_post_purchase_entry_creates_balanced_entry(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    accs = _seed_accounts(
        db,
        tenant_id,
        [
            (CODE_INVENTORY, "ASSET"),
            (CODE_VAT_INPUT, "ASSET"),
            (CODE_AP, "LIABILITY"),
        ],
    )
    purchase = _make_purchase(db, tenant_id)

    entry = post_purchase_entry(db, purchase, user_id=None)

    assert entry is not None
    assert entry.status == "POSTED"
    assert entry.ref_doc_type == "purchase"
    assert entry.debit_total == entry.credit_total

    debits = {l.account_id: l.debit for l in entry.lines if l.debit > 0}
    credits = {l.account_id: l.credit for l in entry.lines if l.credit > 0}
    assert accs[CODE_INVENTORY].id in debits
    assert accs[CODE_VAT_INPUT].id in debits
    assert credits[accs[CODE_AP].id] == Decimal("120")


def test_post_purchase_entry_skips_without_accounts(db, tenant_minimal, caplog):
    tenant_id = tenant_minimal["tenant_id"]
    purchase = _make_purchase(db, tenant_id)
    with caplog.at_level("WARNING"):
        assert post_purchase_entry(db, purchase, None) is None
    assert any("cuentas por defecto faltantes" in r.message for r in caplog.records)


def test_post_purchase_entry_idempotent(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    _seed_accounts(
        db,
        tenant_id,
        [
            (CODE_INVENTORY, "ASSET"),
            (CODE_VAT_INPUT, "ASSET"),
            (CODE_AP, "LIABILITY"),
        ],
    )
    purchase = _make_purchase(db, tenant_id)
    e1 = post_purchase_entry(db, purchase, None)
    e2 = post_purchase_entry(db, purchase, None)
    assert e1 and e2 and e1.id != e2.id
    db.refresh(e1)
    assert e1.status == "CANCELLED"
    assert e2.status == "POSTED"
