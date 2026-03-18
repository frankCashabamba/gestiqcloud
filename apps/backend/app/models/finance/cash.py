"""Cash Position & Cash Flow Models"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args


class CashPosition(Base):
    """
    Posición de caja diaria por cuenta bancaria.

    Attributes:
        bank_account_id: Referencia a cuenta bancaria (ChartOfAccounts)
        position_date: Fecha de la posición
        opening_balance: Saldo inicial del período
        inflows: Total ingresos del período
        outflows: Total egresos del período
        closing_balance: Saldo final (opening + inflows - outflows)
        currency: Moneda (EUR, USD, etc)
    """

    __tablename__ = "cash_positions"
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

    # Date
    position_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha de la posición de caja"
    )

    # Amounts
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo inicial del período"
    )
    inflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total ingresos"
    )
    outflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total egresos"
    )
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0,
        comment="Saldo final = opening + inflows - outflows",
    )

    # Currency
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", comment="ISO 4217 currency code"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class BankStatement(Base):
    """Extracto bancario importado — coincide con migración 014_reconciliation_tables."""

    __tablename__ = "bank_statements"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_format: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="imported")
    total_transactions: Mapped[int] = mapped_column(nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(nullable=False, default=0)
    unmatched_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relations
    lines: Mapped[list["BankStatementLine"]] = relationship(
        "BankStatementLine",
        back_populates="statement",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class BankStatementLine(Base):
    """Línea de extracto bancario — coincide con migración 014 (statement_lines)."""

    __tablename__ = "statement_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    statement_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bank_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    matched_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmatched")
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Relations
    statement: Mapped["BankStatement"] = relationship(
        BankStatement, back_populates="lines", lazy="select"
    )


class CashProjection(Base):
    """
    Proyección de flujo de caja (forecast).

    Attributes:
        bank_account_id: Cuenta bancaria
        projection_date: Fecha de la proyección
        period_days: Número de días proyectados
        projected_inflows: Ingresos proyectados
        projected_outflows: Egresos proyectados
        projected_balance: Saldo proyectado
        scenario: OPTIMISTIC, BASE, PESSIMISTIC
    """

    __tablename__ = "cash_projections"
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

    # Projection info
    projection_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha de la proyección"
    )
    projection_end_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Fecha fin de proyección"
    )
    period_days: Mapped[int] = mapped_column(
        nullable=False, default=30, comment="Número de días proyectados"
    )

    # Projected amounts
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo de apertura"
    )
    projected_inflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Ingresos proyectados"
    )
    projected_outflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Egresos proyectados"
    )
    projected_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo proyectado"
    )

    # Scenario
    scenario: Mapped[str] = mapped_column(
        String(20), nullable=False, default="BASE", comment="OPTIMISTIC, BASE, PESSIMISTIC"
    )

    # Currency
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
