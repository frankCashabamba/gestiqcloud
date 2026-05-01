from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import ChartOfAccounts, JournalEntry, JournalEntryLine
from app.models.accounting.period import AccountingPeriod


@dataclass(frozen=True)
class JournalLineIn:
    account_id: UUID
    debit: Decimal
    credit: Decimal
    description: str | None = None
    line_number: int = 0


# ---------------------------------------------------------------------------
# Concurrency-safe numbering
# ---------------------------------------------------------------------------


def _is_postgres(db: Session) -> bool:
    try:
        return db.bind.dialect.name == "postgresql"  # type: ignore[union-attr]
    except Exception:
        return False


def _acquire_sequence_lock(db: Session, tenant_id: UUID, year: int) -> None:
    """Adquiere lock transaccional para serializar la generación del siguiente número.

    En Postgres usa pg_advisory_xact_lock(hashtext(key)) — se libera al COMMIT.
    En otros motores se hace upsert + SELECT sobre journal_sequences (sin lock fuerte).
    """
    key = f"journal_seq:{tenant_id}:{year}"
    if _is_postgres(db):
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": key})


def generate_entry_number(db: Session, tenant_id: UUID, year: int) -> str:
    """Genera número único de asiento: ASI-YYYY-NNNN (tenant-scoped, concurrencia-safe).

    Estrategia:
    1. pg_advisory_xact_lock(hashtext(tenant+year)) → serializa por (tenant,año).
    2. INSERT ... ON CONFLICT UPDATE RETURNING en `journal_sequences` para incrementar
       atómicamente el contador autoritativo.
    3. Fallback al MAX(number) si la tabla no existe (compatibilidad pre-migración).
    """
    _acquire_sequence_lock(db, tenant_id, year)

    next_num: int | None = None
    try:
        if _is_postgres(db):
            row = db.execute(
                text(
                    "INSERT INTO journal_sequences(tenant_id, year, last_number) "
                    "VALUES (:t, :y, 1) "
                    "ON CONFLICT (tenant_id, year) DO UPDATE "
                    "SET last_number = journal_sequences.last_number + 1 "
                    "RETURNING last_number"
                ),
                {"t": str(tenant_id), "y": year},
            ).first()
            if row:
                next_num = int(row[0])
        else:
            row = db.execute(
                text(
                    "SELECT last_number FROM journal_sequences "
                    "WHERE tenant_id = :t AND year = :y"
                ),
                {"t": str(tenant_id), "y": year},
            ).first()
            current = int(row[0]) if row else 0
            next_num = current + 1
            if row is None:
                db.execute(
                    text(
                        "INSERT INTO journal_sequences(tenant_id, year, last_number) "
                        "VALUES (:t, :y, :n)"
                    ),
                    {"t": str(tenant_id), "y": year, "n": next_num},
                )
            else:
                db.execute(
                    text(
                        "UPDATE journal_sequences SET last_number = :n "
                        "WHERE tenant_id = :t AND year = :y"
                    ),
                    {"n": next_num, "t": str(tenant_id), "y": year},
                )
    except SQLAlchemyError:
        next_num = None

    if next_num is None:
        # Fallback legacy: derivar del MAX(number).
        prefix_legacy = f"ASI-{year}-"
        stmt = (
            select(JournalEntry.number)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.number.like(f"{prefix_legacy}%"),
            )
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

    return f"ASI-{year}-{next_num:04d}"


# ---------------------------------------------------------------------------
# Period validation
# ---------------------------------------------------------------------------


def assert_period_open(db: Session, tenant_id: UUID, entry_date: date) -> None:
    """Lanza HTTP 409 `periodo_cerrado` si la fecha cae en un período CLOSED."""
    try:
        stmt = select(AccountingPeriod.status).where(
            AccountingPeriod.tenant_id == tenant_id,
            AccountingPeriod.year == entry_date.year,
            AccountingPeriod.month == entry_date.month,
        )
        status_value = db.execute(stmt).scalar_one_or_none()
    except SQLAlchemyError:
        return  # Tabla aún no migrada — no bloquear.
    if status_value == "CLOSED":
        raise HTTPException(status_code=409, detail="periodo_cerrado")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

    debit_total = sum((_as_dec(line.debit) for line in lines), Decimal("0"))
    credit_total = sum((_as_dec(line.credit) for line in lines), Decimal("0"))
    if (debit_total - credit_total).copy_abs() > Decimal("0.01"):
        raise ValueError(f"journal_entry_not_balanced debit={debit_total} credit={credit_total}")

    # Bloqueo por período cerrado (HTTP 409 propagado).
    assert_period_open(db, tenant_id, entry_date)

    number = generate_entry_number(db, tenant_id, entry_date.year)
    now = datetime.now(UTC)
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

    for i, line in enumerate(lines, start=1):
        db.add(
            JournalEntryLine(
                entry_id=entry.id,
                account_id=line.account_id,
                debit=_as_dec(line.debit),
                credit=_as_dec(line.credit),
                description=line.description,
                line_number=int(line.line_number or i),
            )
        )

        # Update account balances incrementally for POSTED entries.
        acct = db.get(ChartOfAccounts, line.account_id)
        if acct:
            acct.debit_balance = _as_dec(acct.debit_balance or 0) + _as_dec(line.debit)
            acct.credit_balance = _as_dec(acct.credit_balance or 0) + _as_dec(line.credit)
            acct.balance = _as_dec(acct.debit_balance or 0) - _as_dec(acct.credit_balance or 0)
            db.add(acct)

    db.flush()
    return entry
