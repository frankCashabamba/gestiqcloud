"""
Base models for payments.

Common hierarchy for:
- Payment: Bank-linked invoice payments (reconciliation)
- POSPayment: Immediate POS payments
- AdvancePayment: Future deposits/advances
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    DIRECT_DEBIT = "direct_debit"
    CHECK = "check"
    STORE_CREDIT = "store_credit"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """Payment statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentBase:
    """
    Abstract mixin for all payments (not mapped directly).
    """

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, comment="Payment amount")

    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", comment="Currency (ISO 4217)"
    )

    method: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Payment method (cash, card, transfer, etc.)"
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="Payment status"
    )

    reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="External reference (transaction id, etc.)"
    )

    notes: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Notes")

    paid_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="Payment datetime")

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, comment="Record creation datetime"
    )

    def is_completed(self) -> bool:
        """Check if payment is completed."""
        return self.status == PaymentStatus.COMPLETED.value

    def is_pending(self) -> bool:
        """Check if payment is pending."""
        return self.status == PaymentStatus.PENDING.value

    def can_refund(self) -> bool:
        """Check if payment can be refunded."""
        return self.status == PaymentStatus.COMPLETED.value


# DOCUMENTACIÓN DE USO
#
# Los modelos existentes deben migrar gradualmente a usar este mixin:
#
# 1. Payment (facturacion) - Pagos bancarios con conciliación:
#    - Vinculado a BankTransaction
#    - Vinculado a Invoice
#    - Usado para conciliación bancaria
#
# 2. POSPayment - Pagos inmediatos en POS:
#    - Vinculado a POSReceipt
#    - Múltiples pagos por recibo (split payments)
#    - Confirmación inmediata
#
# 3. AdvancePayment (futuro) - Anticipos:
#    - Vinculado a SalesOrder o Invoice
#    - Se descuenta del total a pagar
#    - Puede tener vencimiento
#
# Ejemplo de implementación:
#
# from app.models.core.payment import PaymentBase, PaymentMethod, PaymentStatus
# from app.config.database import Base
#
# class Payment(PaymentBase, Base):
#     __tablename__ = "payments"
#
#     id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
#     tenant_id: Mapped[UUID] = mapped_column(
#         PGUUID(as_uuid=True),
#         ForeignKey("tenants.id")
#     )
#
#     # Campos específicos de Payment bancario
#     bank_tx_id: Mapped[UUID] = mapped_column(
#         PGUUID(as_uuid=True),
#         ForeignKey("bank_transactions.id")
#     )
#     invoice_id: Mapped[UUID] = mapped_column(
#         PGUUID(as_uuid=True),
#         ForeignKey("invoices.id")
#     )
#
# class POSPayment(PaymentBase, Base):
#     __tablename__ = "pos_payments"
#
#     id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
#     receipt_id: Mapped[UUID] = mapped_column(
#         PGUUID(as_uuid=True),
#         ForeignKey("pos_receipts.id")
#     )
#
#     # Campos específicos de POS
#     # (ninguno adicional necesario actualmente)
