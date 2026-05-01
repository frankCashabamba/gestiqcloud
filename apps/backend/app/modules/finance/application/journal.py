"""
FinanceJournalService - asientos contables automáticos para movimientos de caja
manuales (CashMovement).

INCOME → DEBE Caja (1.1.01) / HABER cuenta de contrapartida (categoría)
EXPENSE → DEBE cuenta de gasto (categoría) / HABER Caja (1.1.01)

Idempotente vía (ref_doc_type='cash_movement', ref_doc_id=<movement.id>). Si no
hay cuentas configuradas se loguea warning y se omite (no bloquea el movimiento).
"""

from __future__ import annotations

import logging
from datetime import date as _date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import ChartOfAccounts, JournalEntry
from app.models.accounting.pos_settings import TenantAccountingSettings
from app.models.finance.cash_management import CashMovement
from app.modules.accounting.application.journal_service import (
    JournalLineIn,
    _as_dec,
    create_posted_entry,
)

logger = logging.getLogger(__name__)

CODE_CASH = "1.1.01"
CODE_DEFAULT_INCOME = "4.1"
CODE_DEFAULT_EXPENSE = "5.1"


def _find_account(db: Session, tenant_id: UUID, code: str) -> ChartOfAccounts | None:
    return db.execute(
        select(ChartOfAccounts).where(
            ChartOfAccounts.tenant_id == tenant_id,
            ChartOfAccounts.code == code,
        )
    ).scalars().first()


def _settings(db: Session, tenant_id: UUID) -> TenantAccountingSettings | None:
    return db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()


def _find_existing_entry(db: Session, movement_id: UUID) -> JournalEntry | None:
    return db.execute(
        select(JournalEntry).where(
            JournalEntry.ref_doc_type == "cash_movement",
            JournalEntry.ref_doc_id == movement_id,
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


def post_cash_movement_entry(
    db: Session,
    movement: CashMovement,
    user_id: UUID | None,
) -> JournalEntry | None:
    """Genera asiento para un movimiento manual de caja."""
    try:
        tenant_id = UUID(str(movement.tenant_id))
        amount = _as_dec(movement.amount or 0)
        if amount <= 0:
            return None

        cfg = _settings(db, tenant_id)
        cash_acct = _find_account(db, tenant_id, CODE_CASH)
        if cfg is not None and getattr(cfg, "cash_account_id", None):
            cash_acct = db.get(ChartOfAccounts, cfg.cash_account_id) or cash_acct

        kind = (movement.type or "").upper()
        if kind == "INCOME":
            counterpart = _find_account(db, tenant_id, CODE_DEFAULT_INCOME)
        else:
            counterpart = _find_account(db, tenant_id, CODE_DEFAULT_EXPENSE)
            if cfg is not None and getattr(cfg, "default_expense_account_id", None):
                counterpart = (
                    db.get(ChartOfAccounts, cfg.default_expense_account_id) or counterpart
                )

        if not (cash_acct and counterpart):
            logger.warning(
                "post_cash_movement_entry: cuentas por defecto faltantes (tenant=%s movement=%s) - skip",
                tenant_id, movement.id,
            )
            return None

        existing = _find_existing_entry(db, movement.id)
        if existing:
            _reverse_entry(db, existing)

        if kind == "INCOME":
            lines = [
                JournalLineIn(account_id=cash_acct.id, debit=amount, credit=Decimal("0")),
                JournalLineIn(account_id=counterpart.id, debit=Decimal("0"), credit=amount),
            ]
        else:
            lines = [
                JournalLineIn(account_id=counterpart.id, debit=amount, credit=Decimal("0")),
                JournalLineIn(account_id=cash_acct.id, debit=Decimal("0"), credit=amount),
            ]

        entry_date = movement.date if isinstance(movement.date, _date) else _date.today()
        return create_posted_entry(
            db,
            tenant_id=tenant_id,
            entry_date=entry_date,
            description=f"Caja: {movement.description or movement.id}",
            ref_doc_type="cash_movement",
            ref_doc_id=movement.id,
            created_by=user_id,
            lines=lines,
        )
    except Exception:
        logger.exception(
            "Could not create journal entry for cash_movement %s",
            getattr(movement, "id", None),
        )
        return None


def reverse_cash_movement_entry(db: Session, movement_id: UUID) -> None:
    try:
        existing = _find_existing_entry(db, movement_id)
        if existing:
            _reverse_entry(db, existing)
    except Exception:
        logger.exception(
            "Could not reverse journal entry for cash_movement %s", movement_id
        )

