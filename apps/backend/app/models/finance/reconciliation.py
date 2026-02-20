"""Bank Reconciliation Models"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Boolean, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

# Enums
reconciliation_status = SQLEnum(
    "DRAFT",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    name="reconciliation_status",
    create_type=False,
)

match_status = SQLEnum(
    "UNMATCHED",
    "SUGGESTED",
    "MATCHED",
    "DISPUTED",
    name="match_status",
    create_type=False,
)


class BankReconciliation(Base):
    """
    Conciliación bancaria por período.

    Attributes:
        bank_account_id: Cuenta bancaria
        period_start, period_end: Período de conciliación
        bank_opening_balance: Saldo apertura según banco
        bank_closing_balance: Saldo cierre según banco
        system_opening_balance: Saldo apertura según sistema
        system_closing_balance: Saldo cierre según sistema
        difference: Diferencia (bank - system)
        status: DRAFT, IN_PROGRESS, COMPLETED, CANCELLED
    """

    __tablename__ = "bank_reconciliations"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Account reference
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("chart_of_accounts"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Period
    period_start: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha inicio período"
    )
    period_end: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha fin período"
    )

    # Bank balances
    bank_opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo apertura según banco"
    )
    bank_closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo cierre según banco"
    )

    # System balances
    system_opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo apertura según sistema"
    )
    system_closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo cierre según sistema"
    )

    # Difference
    difference: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0,
        comment="Diferencia = bank_closing - system_closing",
    )
    is_balanced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="True if difference = 0"
    )

    # Status and notes
    status: Mapped[str] = mapped_column(
        reconciliation_status,
        nullable=False,
        default="DRAFT",
        comment="DRAFT, IN_PROGRESS, COMPLETED, CANCELLED",
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Notas sobre la conciliación"
    )

    # Audit
    reconciled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Usuario que reconcilió"
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha de reconciliación"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    matches: Mapped[list["ReconciliationMatch"]] = relationship(
        "ReconciliationMatch",
        back_populates="reconciliation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    differences: Mapped[list["ReconciliationDifference"]] = relationship(
        "ReconciliationDifference",
        back_populates="reconciliation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReconciliationMatch(Base):
    """
    Coincidencia entre línea de extracto bancario y transacción del sistema.

    Attributes:
        reconciliation_id: Conciliación padre
        bank_statement_line_id: Línea de extracto
        journal_entry_line_id: Línea contable (referencia)
        matched_amount: Monto coincidido
        match_date: Fecha del match
        status: UNMATCHED, SUGGESTED, MATCHED, DISPUTED
    """

    __tablename__ = "reconciliation_matches"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("bank_reconciliations"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Bank statement line
    bank_statement_line_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("bank_statement_lines"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # System transaction (flexible reference)
    ref_doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo de documento (invoice, payment, journal_entry, etc)",
    )
    ref_doc_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, comment="ID del documento"
    )

    # Match details
    matched_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Monto coincidido"
    )
    match_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha del match"
    )

    # Status
    status: Mapped[str] = mapped_column(
        match_status,
        nullable=False,
        default="UNMATCHED",
        comment="UNMATCHED, SUGGESTED, MATCHED, DISPUTED",
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Notas sobre el match"
    )

    # Audit
    matched_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Usuario que hizo el match"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    reconciliation: Mapped["BankReconciliation"] = relationship(
        "BankReconciliation", back_populates="matches", lazy="select"
    )


class ReconciliationDifference(Base):
    """
    Diferencia identificada en la conciliación.

    Attributes:
        reconciliation_id: Conciliación padre
        description: Descripción de la diferencia
        amount: Monto de la diferencia
        difference_type: MISSING, EXTRA, AMOUNT_MISMATCH, DATE_MISMATCH
        resolution: RESOLVED, PENDING, IGNORED
    """

    __tablename__ = "reconciliation_differences"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("bank_reconciliations"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Description and amount
    description: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Descripción de la diferencia"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Monto de la diferencia"
    )

    # Type
    difference_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="MISSING (en banco, no en sistema), EXTRA (en sistema, no en banco), etc",
    )

    # Resolution
    resolution: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", comment="RESOLVED, PENDING, IGNORED"
    )

    # Reference to missing/extra transaction
    ref_doc_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_doc_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Audit
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Usuario que resolvió"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha de resolución"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    reconciliation: Mapped["BankReconciliation"] = relationship(
        "BankReconciliation", back_populates="differences", lazy="select"
    )
