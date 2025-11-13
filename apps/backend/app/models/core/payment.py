"""
Modelos base para pagos.

Define una jerarquía común para todos los tipos de pagos:
- Payment: Pagos bancarios vinculados a facturas (conciliación)
- POSPayment: Pagos inmediatos en punto de venta
- AdvancePayment: Anticipos y señas

Esto permite:
- Reutilización de lógica de pagos
- Reporting unificado
- Facilita conciliación entre sistemas
"""

from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from sqlalchemy import String, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum


class PaymentMethod(str, Enum):
    """Métodos de pago soportados"""
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
    """Estados de pago"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentBase:
    """
    Clase base abstracta (mixin) para todos los pagos.
    
    Define los campos comunes que todo pago debe tener.
    No se mapea a una tabla, solo provee estructura común.
    """
    
    # Campos comunes
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Monto del pago"
    )
    
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
        comment="Moneda (ISO 4217)"
    )
    
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Método de pago (cash, card, transfer, etc.)"
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="Estado del pago"
    )
    
    reference: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Referencia externa (número de transacción, etc.)"
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Notas adicionales"
    )
    
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Fecha/hora del pago"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        comment="Fecha de creación del registro"
    )
    
    def is_completed(self) -> bool:
        """Verifica si el pago está completado"""
        return self.status == PaymentStatus.COMPLETED.value
    
    def is_pending(self) -> bool:
        """Verifica si el pago está pendiente"""
        return self.status == PaymentStatus.PENDING.value
    
    def can_refund(self) -> bool:
        """Verifica si el pago puede ser reembolsado"""
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
