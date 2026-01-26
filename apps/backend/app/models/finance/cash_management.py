"""
Finance - Caja Models

Sistema de gestión de caja diaria:
- Movimientos de caja (ingresos/egresos)
- Cierres diarios de caja
- Conciliación y saldos
- Auditoría completa

Multi-moneda y multi-usuario.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, TIMESTAMP, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, schema_column, schema_table_args

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


# Enums
cash_movement_type = SQLEnum(
    "INCOME",  # Entrada de efectivo
    "EXPENSE",  # Salida de efectivo
    "ADJUSTMENT",  # Ajuste de caja
    name="cash_movement_type",
    create_type=False,
)

cash_movement_category = SQLEnum(
    "SALE",  # Cobro de venta
    "PURCHASE",  # Pago de compra
    "EXPENSE",  # Gastos operativos
    "PAYROLL",  # Pago de nóminas
    "BANK",  # Transferencia banco <-> caja
    "CHANGE",  # Cambio de fondo
    "ADJUSTMENT",  # Ajustes de cuadre
    "OTHER",  # Otros movimientos
    name="cash_movement_category",
    create_type=False,
)

cash_closing_status = SQLEnum(
    "OPEN",  # Caja abierta (día en curso)
    "CLOSED",  # Caja cerrada (cuadrada)
    "PENDING",  # Pendiente de revisar (descuadre)
    name="cash_closing_status",
    create_type=False,
)


class CashMovement(Base):
    """
    Cash Movement - Individual cash income/expense record.

    Attributes:
        type: INCOME, EXPENSE, ADJUSTMENT
        category: SALES, PURCHASES, EXPENSE, PAYROLL, BANK, CHANGE, ADJUSTMENT, OTHER
        amount: Amount (positive for income, negative for expense)
        currency: Currency code (EUR, USD, etc.)
        description: Movement description
        ref_doc_type: Source document type (invoice, receipt, expense, etc.)
        ref_doc_id: Source document ID
        user_id: User who recorded the movement
        cash_box_id: Cash box/POS (optional, for multi-cash)
    """

    __tablename__ = "cash_movements"
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

    # Type and category
    type: Mapped[str] = mapped_column(
        cash_movement_type, nullable=False, index=True, comment="INCOME, EXPENSE, ADJUSTMENT"
    )
    category: Mapped[str] = mapped_column(
        cash_movement_category,
        nullable=False,
        index=True,
        comment="SALES, PURCHASES, EXPENSE, PAYROLL, BANK, CHANGE, ADJUSTMENT, OTHER",
    )

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Amount (positive=income, negative=expense)",
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, comment="ISO 4217 currency code"
    )

    # Description
    description: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Movement description"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reference to source document
    ref_doc_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Document type (invoice, receipt, expense, payroll)"
    )
    ref_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Source document ID"
    )

    # Multi-cash box (optional)
    cash_box_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Cash box/POS ID (for multi-cash)",
    )

    # Responsible user
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="User who recorded the movement"
    )

    # Date
    date: Mapped[date] = mapped_column(Date(), nullable=False, index=True, comment="Movement date")

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relation to closing
    closing_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("cash_closings"), ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class CashClosing(Base):
    """
    Cash Closing - Daily cash reconciliation.

    Attributes:
        date: Closing date
        cash_box_id: Cash box ID (optional, for multi-cash)
        currency: Closing currency

        Balances:
        - opening_balance: Balance at start of day
        - total_income: Sum of day's income
        - total_expense: Sum of day's expenses
        - theoretical_balance: opening_balance + income - expense
        - physical_balance: Physically counted cash
        - difference: physical_balance - theoretical_balance

        Status:
        - status: OPEN, CLOSED, PENDING
        - is_balanced: True if difference = 0

        User:
        - opened_by: User who opened cash
        - closed_by: User who closed cash
    """

    __tablename__ = "cash_closings"
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

    # Date and cash box
    date: Mapped[date] = mapped_column(Date(), nullable=False, index=True, comment="Closing date")
    cash_box_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True, comment="Cash box ID (for multi-cash)"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # === BALANCES ===
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Balance at start of day"
    )
    total_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Sum of day's income"
    )
    total_expense: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Sum of day's expenses (absolute value)",
    )
    theoretical_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Theoretical balance (opening + income - expense)",
    )
    physical_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Physically counted cash"
    )
    difference: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Difference (physical - theoretical)"
    )

    # === STATUS ===
    status: Mapped[str] = mapped_column(cash_closing_status, nullable=False, index=True)
    is_balanced: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="True if difference = 0"
    )

    # === DETAILS ===
    bill_breakdown: Mapped[dict | None] = mapped_column(
        JSON_TYPE, nullable=True, comment="Breakdown of bills and coins counted"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === USERS ===
    opened_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )
