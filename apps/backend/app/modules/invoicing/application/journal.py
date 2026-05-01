"""
InvoicingJournalService - asientos contables automáticos al emitir facturas.

Doble entrada al emitir factura (similar a venta):
  DEBE  1.1.02 Clientes (cuentas por cobrar)   $total
  HABER 4.1    Ventas                          $subtotal
  HABER 2.1.04 IVA por pagar                   $tax

Idempotente: revierte el asiento previo si existe; no bloquea la emisión si fallan
las cuentas por defecto.
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
from app.models.core.facturacion import Invoice
from app.modules.accounting.application.journal_service import (
    JournalLineIn,
    _as_dec,
    create_posted_entry,
)

logger = logging.getLogger(__name__)

CODE_AR = "1.1.02"
CODE_SALES = "4.1"
CODE_VAT_OUTPUT = "2.1.04"


def _find_account(db: Session, tenant_id: UUID, code: str) -> ChartOfAccounts | None:
    return db.execute(
        select(ChartOfAccounts).where(
            ChartOfAccounts.tenant_id == tenant_id,
            ChartOfAccounts.code == code,
        )
    ).scalars().first()


def _settings(db: Session, tenant_id: UUID) -> TenantAccountingSettings | None:
    return db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()


def _find_existing_entry(db: Session, invoice_id: UUID) -> JournalEntry | None:
    return db.execute(
        select(JournalEntry).where(
            JournalEntry.ref_doc_type == "invoice",
            JournalEntry.ref_doc_id == invoice_id,
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


def _parse_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return date.today()


def post_invoice_entry(
    db: Session,
    invoice: Invoice,
    user_id: UUID | None,
) -> JournalEntry | None:
    """Genera asiento al emitir factura. Devuelve None si se omite por error."""
    try:
        tenant_id = UUID(str(invoice.tenant_id))
        total = _as_dec(invoice.total or 0)
        subtotal = _as_dec(invoice.subtotal or 0)
        tax = _as_dec(getattr(invoice, "tax", 0) or 0)
        if total <= 0:
            return None

        cfg = _settings(db, tenant_id)
        sales_acct = _find_account(db, tenant_id, CODE_SALES)
        if cfg is not None and getattr(cfg, "sales_bakery_account_id", None):
            sales_acct = db.get(ChartOfAccounts, cfg.sales_bakery_account_id) or sales_acct
        vat_acct = _find_account(db, tenant_id, CODE_VAT_OUTPUT)
        if cfg is not None and getattr(cfg, "vat_output_account_id", None):
            vat_acct = db.get(ChartOfAccounts, cfg.vat_output_account_id) or vat_acct
        ar_acct = _find_account(db, tenant_id, CODE_AR)

        if not (ar_acct and sales_acct):
            logger.warning(
                "post_invoice_entry: cuentas por defecto faltantes (tenant=%s invoice=%s) - skip",
                tenant_id, invoice.id,
            )
            return None

        existing = _find_existing_entry(db, invoice.id)
        if existing:
            _reverse_entry(db, existing)

        lines: list[JournalLineIn] = [
            JournalLineIn(account_id=ar_acct.id, debit=total, credit=Decimal("0")),
        ]
        if tax > 0 and vat_acct is not None:
            lines.append(JournalLineIn(account_id=sales_acct.id, debit=Decimal("0"), credit=subtotal))
            lines.append(JournalLineIn(account_id=vat_acct.id, debit=Decimal("0"), credit=tax))
        else:
            lines.append(
                JournalLineIn(account_id=sales_acct.id, debit=Decimal("0"), credit=subtotal + tax)
            )

        entry_date = _parse_date(invoice.issue_date)
        return create_posted_entry(
            db,
            tenant_id=tenant_id,
            entry_date=entry_date,
            description=f"Factura: {invoice.number or invoice.id}",
            ref_doc_type="invoice",
            ref_doc_id=invoice.id,
            created_by=user_id,
            lines=lines,
        )
    except Exception:
        logger.exception(
            "Could not create journal entry for invoice %s",
            getattr(invoice, "id", None),
        )
        return None


def reverse_invoice_entry(db: Session, invoice_id: UUID) -> None:
    try:
        existing = _find_existing_entry(db, invoice_id)
        if existing:
            _reverse_entry(db, existing)
    except Exception:
        logger.exception("Could not reverse journal entry for invoice %s", invoice_id)

