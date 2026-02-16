from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import (
    ChartOfAccounts,
    JournalEntry,
    JournalEntryLine,
)


@dataclass(frozen=True)
class JournalLineIn:
    account_id: UUID
    debit: Decimal
    credit: Decimal
    description: str | None = None
    line_number: int = 0


def generate_entry_number(db: Session, tenant_id: UUID, year: int) -> str:
    """Genera número único de asiento: ASI-YYYY-NNNN (tenant-scoped)."""
    prefix = f"ASI-{year}-"
    stmt = (
        select(JournalEntry.number)
        .where(JournalEntry.tenant_id == tenant_id, JournalEntry.number.like(f"{prefix}%"))
        .order_by(JournalEntry.number.desc())
        .limit(1)
    )
    last = db.execute(stmt).scalar_one_or_none()
    if last:
        try:
            next_num = int(str(last).split("-")[-1]) + 1
        except Exception:
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}{next_num:04d}"


def _as_dec(v: Decimal | int | float | str) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def create_posted_entry(
    db: Session,
    *,
    tenant_id: UUID,
    entry_date: date,
    description: str,
    ref_doc_type: str,
    ref_doc_id: UUID,
    created_by: UUID | None,
    lines: list[JournalLineIn],
) -> JournalEntry:
    """Crea y contabiliza (POSTED) un asiento y actualiza saldos de cuentas."""
    if len(lines) < 2:
        raise ValueError("journal_entry_requires_min_2_lines")

    debit_total = sum((_as_dec(l.debit) for l in lines), Decimal("0"))
    credit_total = sum((_as_dec(l.credit) for l in lines), Decimal("0"))
    if (debit_total - credit_total).copy_abs() > Decimal("0.01"):
        raise ValueError(f"journal_entry_not_balanced debit={debit_total} credit={credit_total}")

    number = generate_entry_number(db, tenant_id, entry_date.year)
    now = datetime.utcnow()
    entry = JournalEntry(
        tenant_id=tenant_id,
        number=number,
        date=entry_date,
        type="OPERATIONS",
        description=description,
        debit_total=debit_total,
        credit_total=credit_total,
        is_balanced=True,
        status="POSTED",
        ref_doc_type=ref_doc_type,
        ref_doc_id=ref_doc_id,
        created_by=created_by,
        posted_by=created_by,
        posted_at=now,
    )
    db.add(entry)
    db.flush()

    for i, l in enumerate(lines, start=1):
        db.add(
            JournalEntryLine(
                entry_id=entry.id,
                account_id=l.account_id,
                debit=_as_dec(l.debit),
                credit=_as_dec(l.credit),
                description=l.description,
                line_number=int(l.line_number or i),
            )
        )

        # Update account balances incrementally for POSTED entries.
        acct = db.get(ChartOfAccounts, l.account_id)
        if acct:
            acct.debit_balance = _as_dec(acct.debit_balance or 0) + _as_dec(l.debit)
            acct.credit_balance = _as_dec(acct.credit_balance or 0) + _as_dec(l.credit)
            acct.balance = _as_dec(acct.debit_balance or 0) - _as_dec(acct.credit_balance or 0)
            db.add(acct)

    db.flush()
    return entry

