"""Payment Tracking & Scheduling Models"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

# Enums
payment_status = SQLEnum(
    "PENDING",
    "IN_PROGRESS",
    "CONFIRMED",
    "FAILED",
    "CANCELLED",
    name="payment_status",
    create_type=False,
)

payment_method = SQLEnum(
    "CASH",
    "BANK_TRANSFER",
    "CARD",
    "CHEQUE",
    "DIRECT_DEBIT",
    "OTHER",
    name="payment_method",
    create_type=False,
)


class Payment(Base):
    """
    Registro de pago (entrada o salida).

    Attributes:
        amount: Monto del pago
        payment_date: Fecha del pago
        payment_method: Método de pago (CASH, BANK_TRANSFER, CARD, etc)
        status: PENDING, IN_PROGRESS, CONFIRMED, FAILED, CANCELLED
        ref_doc_type: Tipo de documento origen (invoice, bill, etc)
        ref_doc_id: ID del documento origen
        bank_account_id: Cuenta bancaria donde se registra
    """

    __tablename__ = "payments"
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

    # Amount and currency
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="Monto del pago"
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", comment="ISO 4217 currency code"
    )

    # Dates
    payment_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha del pago"
    )
    scheduled_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Fecha programada (si está programado)"
    )
    confirmed_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Fecha de confirmación"
    )

    # Method and status
    method: Mapped[str] = mapped_column(
        payment_method,
        nullable=False,
        default="BANK_TRANSFER",
        comment="CASH, BANK_TRANSFER, CARD, CHEQUE, DIRECT_DEBIT, OTHER",
    )
    status: Mapped[str] = mapped_column(
        payment_status,
        nullable=False,
        default="PENDING",
        comment="PENDING, IN_PROGRESS, CONFIRMED, FAILED, CANCELLED",
        index=True,
    )

    # Document reference (invoice, bill, etc)
    ref_doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Tipo de documento (invoice, bill, payroll, etc)"
    )
    ref_doc_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="ID del documento",
        index=True,
    )

    # Bank account
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("chart_of_accounts"), ondelete="SET NULL"),
        nullable=True,
        comment="Cuenta bancaria",
    )

    # Description and notes
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Descripción del pago"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Notas adicionales")

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(
        nullable=False, default=0, comment="Número de reintentos"
    )
    last_error: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Último error ocurrido"
    )

    # Bank reference
    bank_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Referencia del banco (número de transacción)"
    )

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )


class PaymentSchedule(Base):
    """
    Plan de pagos programados (ej: cuotas, pagos recurrentes).

    Attributes:
        ref_doc_id: Documento original (invoice, etc)
        total_amount: Monto total a pagar
        installments: Número de cuotas
        frequency: Frecuencia (MONTHLY, WEEKLY, etc)
        status: ACTIVE, COMPLETED, SUSPENDED, CANCELLED
    """

    __tablename__ = "payment_schedules"
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

    # Reference
    ref_doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Tipo de documento"
    )
    ref_doc_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="ID del documento",
        index=True,
    )

    # Schedule details
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="Monto total a pagar"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    installments: Mapped[int] = mapped_column(nullable=False, default=1, comment="Número de cuotas")
    frequency: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="MONTHLY",
        comment="MONTHLY, WEEKLY, BIWEEKLY, QUARTERLY",
    )

    # Dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False, comment="Fecha de inicio")
    end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Fecha de fin (calculada)"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        comment="ACTIVE, COMPLETED, SUSPENDED, CANCELLED",
    )

    # Tracking
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Monto pagado hasta ahora"
    )
    paid_installments: Mapped[int] = mapped_column(
        nullable=False, default=0, comment="Cuotas pagadas"
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    payments: Mapped[list["Payment"]] = relationship(
        primaryjoin=lambda: foreign(Payment.ref_doc_id) == PaymentSchedule.id,
        viewonly=True,
        lazy="select",
    )
