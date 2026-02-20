"""Cash Position & Cash Flow Models"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_table_args, schema_column

# Enums
statement_source = SQLEnum(
    "MANUAL",  # Manual entry
    "IMPORT",  # Imported from bank
    "SYNC",    # Synced from payment gateway
    name="statement_source",
    create_type=False,
)

statement_status = SQLEnum(
    "DRAFT",
    "POSTED",
    "RECONCILED",
    "CANCELLED",
    name="statement_status",
    create_type=False,
)


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
        Date, nullable=False, index=True,
        comment="Fecha de la posición de caja"
    )
    
    # Amounts
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Saldo inicial del período"
    )
    inflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Total ingresos"
    )
    outflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Total egresos"
    )
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Saldo final = opening + inflows - outflows"
    )
    
    # Currency
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR",
        comment="ISO 4217 currency code"
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, 
        server_default="now()", onupdate=datetime.utcnow
    )


class BankStatement(Base):
    """
    Extracto bancario importado o sincronizado.
    
    Attributes:
        bank_account_id: Cuenta bancaria
        statement_date: Fecha del extracto
        period_start, period_end: Período del extracto
        opening_balance: Saldo de apertura según banco
        closing_balance: Saldo de cierre según banco
        source: MANUAL, IMPORT, SYNC
        status: DRAFT, POSTED, RECONCILED, CANCELLED
    """
    
    __tablename__ = "bank_statements"
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
    
    # Dates
    statement_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        comment="Fecha del extracto"
    )
    period_start: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Fecha inicio período"
    )
    period_end: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Fecha fin período"
    )
    
    # Balances
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Saldo de apertura según banco"
    )
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Saldo de cierre según banco"
    )
    
    # Source and status
    source: Mapped[str] = mapped_column(
        statement_source, nullable=False, default="IMPORT",
        comment="MANUAL, IMPORT, SYNC"
    )
    status: Mapped[str] = mapped_column(
        statement_status, nullable=False, default="DRAFT",
        comment="DRAFT, POSTED, RECONCILED, CANCELLED"
    )
    
    # Currency
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR",
        comment="ISO 4217 currency code"
    )
    
    # Bank reference
    bank_ref: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Reference from bank (statement ID)"
    )
    
    # Audit
    imported_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
    
    # Relations
    lines: Mapped[list["BankStatementLine"]] = relationship(
        "BankStatementLine", back_populates="statement",
        cascade="all, delete-orphan", lazy="selectin"
    )


class BankStatementLine(Base):
    """
    Línea individual de extracto bancario.
    
    Attributes:
        statement_id: Extracto padre
        transaction_date: Fecha de la transacción
        amount: Monto (positivo=entrada, negativo=salida)
        description: Descripción del movimiento
        reference: Referencia del banco (número de operación)
    """
    
    __tablename__ = "bank_statement_lines"
    __table_args__ = schema_table_args()
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Reference
    statement_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("bank_statements"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Data
    transaction_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        comment="Fecha de la transacción"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False,
        comment="Monto (+ entrada, - salida)"
    )
    description: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Descripción del movimiento"
    )
    reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Referencia del banco (número de operación)"
    )
    
    # Line number for ordering
    line_number: Mapped[int] = mapped_column(
        nullable=False, default=0
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
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
        Date, nullable=False, index=True,
        comment="Fecha de la proyección"
    )
    projection_end_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Fecha fin de proyección"
    )
    period_days: Mapped[int] = mapped_column(
        nullable=False, default=30,
        comment="Número de días proyectados"
    )
    
    # Projected amounts
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Saldo de apertura"
    )
    projected_inflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Ingresos proyectados"
    )
    projected_outflows: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Egresos proyectados"
    )
    projected_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0,
        comment="Saldo proyectado"
    )
    
    # Scenario
    scenario: Mapped[str] = mapped_column(
        String(20), nullable=False, default="BASE",
        comment="OPTIMISTIC, BASE, PESSIMISTIC"
    )
    
    # Currency
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR"
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
