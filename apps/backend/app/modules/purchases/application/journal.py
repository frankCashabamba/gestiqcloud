"""
PurchaseJournalService — asientos contables automáticos para órdenes de compra.

Doble entrada al recibir compra:
  DEBE  1.1.03 Inventario / Mercadería   $subtotal
  DEBE  1.1.05 IVA crédito fiscal        $tax
  HABER 2.1.01 Cuentas por pagar         $total

Idempotente: si ya existe asiento POSTED para la compra se reversa antes de crear
uno nuevo. No bloquea la recepción ante error contable.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import ChartOfAccounts, JournalEntry
from app.models.accounting.pos_settings import TenantAccountingSettings
from app.models.purchases.purchase import Purchase
from app.modules.accounting.application.journal_service import (
    JournalLineIn,
    _as_dec,
    create_posted_entry,
)

logger = logging.getLogger(__name__)

CODE_INVENTORY = "1.1.03"
CODE_VAT_INPUT = "1.1.05"
CODE_AP = "2.1.01"


def _find_account(db: Session, tenant_id: UUID, code: str) -> ChartOfAccounts | None:
    return db.execute(
        select(ChartOfAccounts).where(
            ChartOfAccounts.tenant_id == tenant_id,
            ChartOfAccounts.code == code,
        )
    ).scalars().first()


def _settings(db: Session, tenant_id: UUID) -> TenantAccountingSettings | None:
    return db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()


def _find_existing_entry(db: Session, purchase_id: UUID) -> JournalEntry | None:
    return db.execute(
        select(JournalEntry).where(
            JournalEntry.ref_doc_type == "purchase",
            JournalEntry.ref_doc_id == purchase_id,
            JournalEntry.status != "CANCELLED",
        )
    ).scalars().first()


def _reverse_entry(db: Session, entry: JournalEntry) -> None:
    entry.status = "CANCELLED"
    for line in entry.lines:
        acct = db.get(ChartOfAccounts, line.account_id)
        if acct:
            acct.debit_balance = _as_dec(acct.debit_balance or 0) - _as_dec(line.debit)
            acct.credit_balance = _as_dec(acct.credit_balance or 0) - _as_dec(line.credit)
            acct.balance = _as_dec(acct.debit_balance or 0) - _as_dec(acct.credit_balance or 0)
            db.add(acct)
    db.flush()


def post_purchase_entry(
    db: Session,
    purchase: Purchase,
    user_id: UUID | None,
) -> JournalEntry | None:
    try:
        tenant_id = UUID(str(purchase.tenant_id))
        total = _as_dec(purchase.total or 0)
        tax = _as_dec(getattr(purchase, "taxes", 0) or 0)
        subtotal = _as_dec(purchase.subtotal or 0)
        if total <= 0:
            return None

        cfg = _settings(db, tenant_id)
        inv_acct = _find_account(db, tenant_id, CODE_INVENTORY)
        if cfg is not None and getattr(cfg, "default_expense_account_id", None):
            inv_acct = db.get(ChartOfAccounts, cfg.default_expense_account_id) or inv_acct
        vat_acct = _find_account(db, tenant_id, CODE_VAT_INPUT)
        if cfg is not None and getattr(cfg, "vat_input_account_id", None):
            vat_acct = db.get(ChartOfAccounts, cfg.vat_input_account_id) or vat_acct
        ap_acct = _find_account(db, tenant_id, CODE_AP)
        if cfg is not None and getattr(cfg, "ap_account_id", None):
            ap_acct = db.get(ChartOfAccounts, cfg.ap_account_id) or ap_acct

        if not (inv_acct and ap_acct):
            logger.warning(
                "post_purchase_entry: cuentas por defecto faltantes (tenant=%s purchase=%s) — skip",
                tenant_id, purchase.id,
            )
            return None

        existing = _find_existing_entry(db, purchase.id)
        if existing:
            _reverse_entry(db, existing)

        lines: list[JournalLineIn] = [
            JournalLineIn(account_id=inv_acct.id, debit=subtotal, credit=Decimal("0")),
        ]
        if tax > 0 and vat_acct is not None:
            lines.append(JournalLineIn(account_id=vat_acct.id, debit=tax, credit=Decimal("0")))
        else:
            lines[0] = JournalLineIn(account_id=inv_acct.id, debit=subtotal + tax, credit=Decimal("0"))
        lines.append(JournalLineIn(account_id=ap_acct.id, debit=Decimal("0"), credit=total))

        entry_date = purchase.date if isinstance(purchase.date, date) else date.today()
        return create_posted_entry(
            db,
            tenant_id=tenant_id,
            entry_date=entry_date,
            description=f"Compra: {purchase.number or purchase.id}",
            ref_doc_type="purchase",
            ref_doc_id=purchase.id,
            created_by=user_id,
            lines=lines,
        )
    except Exception:
        logger.exception("Could not create journal entry for purchase %s", getattr(purchase, "id", None))
        return None


def reverse_purchase_entry(db: Session, purchase_id: UUID) -> None:
    try:
        existing = _find_existing_entry(db, purchase_id)
        if existing:
            _reverse_entry(db, existing)
    except Exception:
        logger.exception("Could not reverse journal entry for purchase %s", purchase_id)
