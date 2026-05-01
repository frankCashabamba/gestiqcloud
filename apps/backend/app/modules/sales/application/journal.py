"""
SalesJournalService — asientos contables automáticos para órdenes de venta.

Doble entrada al confirmar/cobrar venta:
  DEBE  1.1.02 Clientes (cuentas por cobrar)   $total
  HABER 4.1    Ventas                          $subtotal
  HABER 2.1.04 IVA por pagar                   $tax

Si se marca como pagada (mark_paid) se sustituye Clientes por la cuenta de cobro
configurada (caja/banco) según el método de pago.

Idempotente: si ya existe un asiento POSTED ligado al sales_order se reversa antes
de crear uno nuevo. Cualquier error se loguea y NO bloquea la venta.
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
from app.models.sales.order import SalesOrder
from app.modules.accounting.application.journal_service import (
    JournalLineIn,
    _as_dec,
    create_posted_entry,
)

logger = logging.getLogger(__name__)

# Códigos estándar (alineados con seed _SEED_ACCOUNTS de accounting/interface/http/tenant.py).
CODE_AR = "1.1.02"  # Clientes (cuentas por cobrar)
CODE_SALES = "4.1"  # Ventas (genérica)
CODE_VAT_OUTPUT = "2.1.04"  # IVA por pagar
CODE_CASH = "1.1.01"  # Caja


def _find_account(db: Session, tenant_id: UUID, code: str) -> ChartOfAccounts | None:
    return (
        db.execute(
            select(ChartOfAccounts).where(
                ChartOfAccounts.tenant_id == tenant_id,
                ChartOfAccounts.code == code,
            )
        )
        .scalars()
        .first()
    )


def _settings(db: Session, tenant_id: UUID) -> TenantAccountingSettings | None:
    return db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()


def _find_existing_entry(db: Session, sale_order_id: UUID) -> JournalEntry | None:
    return (
        db.execute(
            select(JournalEntry).where(
                JournalEntry.ref_doc_type == "sales_order",
                JournalEntry.ref_doc_id == sale_order_id,
                JournalEntry.status != "CANCELLED",
            )
        )
        .scalars()
        .first()
    )


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


def post_sale_entry(
    db: Session,
    sale_order: SalesOrder,
    user_id: UUID | None,
    *,
    paid: bool = False,
) -> JournalEntry | None:
    """Genera el asiento de venta. Devuelve el asiento creado o None si se omitió.

    paid=True → contrapartida en cuenta de cobro (caja del tenant settings) en vez
    de Cuentas por Cobrar. Idempotente: revierte el anterior si existía.
    """
    try:
        tenant_id = UUID(str(sale_order.tenant_id))
        total = _as_dec(sale_order.total or 0)
        tax = _as_dec(sale_order.tax or 0)
        subtotal = _as_dec(sale_order.subtotal or 0)
        if total <= 0:
            return None

        # Resolver cuentas por código + settings.
        cfg = _settings(db, tenant_id)
        sales_acct = _find_account(db, tenant_id, CODE_SALES)
        if cfg is not None and getattr(cfg, "sales_bakery_account_id", None):
            sales_acct = db.get(ChartOfAccounts, cfg.sales_bakery_account_id) or sales_acct
        vat_acct = _find_account(db, tenant_id, CODE_VAT_OUTPUT)
        if cfg is not None and getattr(cfg, "vat_output_account_id", None):
            vat_acct = db.get(ChartOfAccounts, cfg.vat_output_account_id) or vat_acct

        if paid and cfg is not None and getattr(cfg, "cash_account_id", None):
            debit_acct = db.get(ChartOfAccounts, cfg.cash_account_id)
        elif paid:
            debit_acct = _find_account(db, tenant_id, CODE_CASH)
        else:
            debit_acct = _find_account(db, tenant_id, CODE_AR)

        if not (debit_acct and sales_acct):
            logger.warning(
                "post_sale_entry: cuentas por defecto faltantes (tenant=%s order=%s) — skip",
                tenant_id,
                sale_order.id,
            )
            return None

        # Idempotencia: revertir asiento anterior si existe.
        existing = _find_existing_entry(db, sale_order.id)
        if existing:
            _reverse_entry(db, existing)

        lines: list[JournalLineIn] = [
            JournalLineIn(account_id=debit_acct.id, debit=total, credit=Decimal("0")),
            JournalLineIn(account_id=sales_acct.id, debit=Decimal("0"), credit=subtotal),
        ]
        if tax > 0 and vat_acct is not None:
            lines.append(JournalLineIn(account_id=vat_acct.id, debit=Decimal("0"), credit=tax))
        else:
            # Sin IVA — fusionar tax en ventas para mantener cuadre.
            lines[1] = JournalLineIn(
                account_id=sales_acct.id, debit=Decimal("0"), credit=subtotal + tax
            )

        entry_date = (
            sale_order.order_date if isinstance(sale_order.order_date, date) else date.today()
        )
        return create_posted_entry(
            db,
            tenant_id=tenant_id,
            entry_date=entry_date,
            description=f"Venta: {sale_order.number or sale_order.id}",
            ref_doc_type="sales_order",
            ref_doc_id=sale_order.id,
            created_by=user_id,
            lines=lines,
        )
    except Exception:
        logger.exception(
            "Could not create journal entry for sales_order %s", getattr(sale_order, "id", None)
        )
        return None


def reverse_sale_entry(db: Session, sale_order_id: UUID) -> None:
    """Revierte el asiento al cancelar una venta."""
    try:
        existing = _find_existing_entry(db, sale_order_id)
        if existing:
            _reverse_entry(db, existing)
    except Exception:
        logger.exception("Could not reverse journal entry for sales_order %s", sale_order_id)
