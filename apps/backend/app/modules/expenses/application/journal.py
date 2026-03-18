"""
ExpenseJournalService — genera asientos contables de doble entrada automáticamente
al crear, actualizar o eliminar un gasto operativo.

Flujo de doble entrada:
  DEBE  6.2.xx  Cuenta de gasto     $total
  HABER 1.1.xx  Caja/Banco          $total   (si pagado)
         ó
  HABER 2.1.01  Cuentas por pagar   $total   (si pendiente)

Las cuentas se resuelven por código en chart_of_accounts del tenant.
Si no existen, se crean automáticamente (can_post=True).
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import ChartOfAccounts, JournalEntry
from app.models.expenses.expense import Expense
from app.modules.accounting.application.journal_service import JournalLineIn, create_posted_entry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Account catalogue — (code, name, type)
# ---------------------------------------------------------------------------

_CATEGORY_ACCOUNTS: dict[str, tuple[str, str, str]] = {
    "payroll":    ("6.2.01", "Gastos de personal",       "EXPENSE"),
    "rent":       ("6.2.02", "Arrendamientos y cánones", "EXPENSE"),
    "supplies":   ("6.2.03", "Suministros",              "EXPENSE"),
    "marketing":  ("6.2.04", "Publicidad y propaganda",  "EXPENSE"),
    "services":   ("6.2.05", "Servicios exteriores",     "EXPENSE"),
    "production": ("6.1.01", "Costo de producción",      "EXPENSE"),
    "other":      ("6.2.99", "Otros gastos operativos",  "EXPENSE"),
}

_PAYMENT_ACCOUNTS: dict[str, tuple[str, str, str]] = {
    "cash":         ("1.1.01", "Caja",                "ASSET"),
    "card":         ("1.1.02", "Tarjetas de crédito", "ASSET"),
    "transfer":     ("1.1.03", "Banco",               "ASSET"),
    "direct_debit": ("1.1.03", "Banco",               "ASSET"),
}

_DEFAULT_EXPENSE  = ("6.2.99", "Otros gastos operativos",      "EXPENSE")
_DEFAULT_PAYABLES = ("2.1.01", "Proveedores / Cuentas por pagar", "LIABILITY")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_account(
    db: Session,
    tenant_id: UUID,
    code: str,
    name: str,
    acc_type: str,
) -> ChartOfAccounts:
    """Devuelve la cuenta por código; la crea si no existe."""
    stmt = select(ChartOfAccounts).where(
        ChartOfAccounts.tenant_id == tenant_id,
        ChartOfAccounts.code == code,
    )
    acct = db.execute(stmt).scalars().first()
    if acct:
        return acct
    acct = ChartOfAccounts(
        tenant_id=tenant_id,
        code=code,
        name=name,
        type=acc_type,
        level=3,
        can_post=True,
        active=True,
        debit_balance=Decimal("0"),
        credit_balance=Decimal("0"),
        balance=Decimal("0"),
    )
    db.add(acct)
    db.flush()
    return acct


def _expense_accounts(
    db: Session,
    tenant_id: UUID,
    category: str | None,
    payment_method: str | None,
    status: str | None,
) -> tuple[ChartOfAccounts, ChartOfAccounts]:
    """Devuelve (cuenta_gasto, cuenta_contrapartida)."""
    exp_code, exp_name, exp_type = _CATEGORY_ACCOUNTS.get(
        str(category or "").lower(), _DEFAULT_EXPENSE
    )
    expense_acct = _resolve_account(db, tenant_id, exp_code, exp_name, exp_type)

    is_paid = str(status or "").lower() in ("paid",)
    pm = str(payment_method or "").lower()
    if is_paid and pm in _PAYMENT_ACCOUNTS:
        cnt_code, cnt_name, cnt_type = _PAYMENT_ACCOUNTS[pm]
    else:
        cnt_code, cnt_name, cnt_type = _DEFAULT_PAYABLES
    contra_acct = _resolve_account(db, tenant_id, cnt_code, cnt_name, cnt_type)

    return expense_acct, contra_acct


def _find_existing_entry(db: Session, expense_id: UUID) -> JournalEntry | None:
    stmt = select(JournalEntry).where(
        JournalEntry.ref_doc_type == "expense",
        JournalEntry.ref_doc_id == expense_id,
        JournalEntry.status != "CANCELLED",
    )
    return db.execute(stmt).scalars().first()


def _reverse_entry(db: Session, entry: JournalEntry) -> None:
    """Revierte un asiento: invierte saldos en las cuentas y lo marca CANCELLED."""
    from app.modules.accounting.application.journal_service import _as_dec

    entry.status = "CANCELLED"
    for line in entry.lines:
        acct = db.get(ChartOfAccounts, line.account_id)
        if acct:
            acct.debit_balance  = _as_dec(acct.debit_balance  or 0) - _as_dec(line.debit)
            acct.credit_balance = _as_dec(acct.credit_balance or 0) - _as_dec(line.credit)
            acct.balance        = _as_dec(acct.debit_balance or 0)  - _as_dec(acct.credit_balance or 0)
            db.add(acct)
    db.flush()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ExpenseJournalService:
    """
    Genera/revierte asientos contables para gastos operativos.
    Todos los métodos son best-effort: loguean errores pero no abortan el commit principal.
    """

    def __init__(self, db: Session, tenant_id: UUID, user_id: UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def on_create(self, expense: Expense) -> None:
        """Genera el asiento inicial al crear un gasto."""
        try:
            total = Decimal(str(float(expense.total or expense.amount or 0)))
            if total <= 0:
                return
            exp_acct, cnt_acct = _expense_accounts(
                self.db, self.tenant_id,
                expense.category, expense.payment_method, expense.status,
            )
            entry_date = expense.date if isinstance(expense.date, date) else date.today()
            create_posted_entry(
                self.db,
                tenant_id=self.tenant_id,
                entry_date=entry_date,
                description=f"Gasto: {expense.concept or 'Sin concepto'}",
                ref_doc_type="expense",
                ref_doc_id=expense.id,
                created_by=self.user_id,
                lines=[
                    JournalLineIn(account_id=exp_acct.id, debit=total,        credit=Decimal("0")),
                    JournalLineIn(account_id=cnt_acct.id, debit=Decimal("0"), credit=total),
                ],
            )
            logger.debug("Journal entry created for expense %s", expense.id)
        except Exception:
            logger.exception("Could not create journal entry for expense %s", expense.id)

    def on_update(self, expense: Expense) -> None:
        """Revierte el asiento anterior y crea uno nuevo con los valores actuales."""
        try:
            existing = _find_existing_entry(self.db, expense.id)
            if existing:
                _reverse_entry(self.db, existing)
            self.on_create(expense)
        except Exception:
            logger.exception("Could not update journal entry for expense %s", expense.id)

    def on_delete(self, expense: Expense) -> None:
        """Revierte el asiento al eliminar el gasto."""
        try:
            existing = _find_existing_entry(self.db, expense.id)
            if existing:
                _reverse_entry(self.db, existing)
        except Exception:
            logger.exception("Could not reverse journal entry for expense %s", expense.id)
