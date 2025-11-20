"""Module: facturacion.py - Invoice and payment models."""

import uuid
from datetime import date
from enum import Enum

from sqlalchemy import JSON, Date
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.core.clients import Client
from app.models.core.invoiceLine import LineaFactura
from app.models.tenant import Tenant

# JSONB with SQLite fallback
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class InvoiceTemp(Base):
    """Temporary invoice import model."""

    __tablename__ = "invoices_temp"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[int] = mapped_column("user_id", ForeignKey("company_users.id"))
    file_name: Mapped[str] = mapped_column("file_name")
    data: Mapped[dict] = mapped_column("data", JSON_TYPE)
    status: Mapped[str] = mapped_column("status", default="pending")
    import_date: Mapped[str] = mapped_column("import_date", server_default=text("now()"))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        "tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])


class Invoice(Base):
    """Invoice model."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    number: Mapped[str] = mapped_column("number", String, nullable=False)
    supplier: Mapped[str] = mapped_column("supplier", String)
    issue_date: Mapped[str] = mapped_column("issue_date", String)
    amount: Mapped[int] = mapped_column("amount", default=0)
    status: Mapped[str] = mapped_column("status", String, default="pending")
    created_at: Mapped[str] = mapped_column("created_at", String, server_default=text("now()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column("tenant_id", ForeignKey("tenants.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(
        "customer_id", UUID(as_uuid=True), ForeignKey("clients.id")
    )
    subtotal: Mapped[float] = mapped_column("subtotal")
    vat: Mapped[float] = mapped_column("vat")
    total: Mapped[float] = mapped_column("total")

    # Relationships
    tenant: Mapped[Tenant] = relationship(Tenant)
    customer: Mapped[Client] = relationship(Client, foreign_keys=[customer_id])
    lines: Mapped[list[LineaFactura]] = relationship(LineaFactura, cascade="all, delete-orphan")


class BankAccount(Base):
    """Bank account model."""

    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        "tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column("name", String)
    iban: Mapped[str] = mapped_column("iban", String, index=True)
    bank: Mapped[str] = mapped_column("bank", String, nullable=True)
    currency: Mapped[str] = mapped_column("currency", String, default="EUR")
    customer_id: Mapped[uuid.UUID] = mapped_column(
        "customer_id", UUID(as_uuid=True), ForeignKey("clients.id")
    )

    customer: Mapped[Client] = relationship(Client)
    tenant = relationship("Tenant", foreign_keys=[tenant_id])


class MovimientoTipo(Enum):
    """Transaction type enum."""

    RECIBO = "receipt"
    TRANSFERENCIA = "transfer"
    TARJETA = "card"
    EFECTIVO = "cash"
    OTRO = "other"


class MovimientoEstado(Enum):
    """Transaction status enum."""

    PENDIENTE = "pending"
    CONCILIADO = "reconciled"
    RECHAZADO = "rejected"


class BankTransaction(Base):
    """Bank transaction model."""

    __tablename__ = "bank_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        "tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        "account_id", UUID(as_uuid=True), ForeignKey("bank_accounts.id"), index=True
    )
    date: Mapped[date] = mapped_column(Date(), index=True)
    amount: Mapped[float] = mapped_column("amount")
    currency: Mapped[str] = mapped_column("currency", String, default="EUR")
    type: Mapped[MovimientoTipo] = mapped_column("type", SAEnum(MovimientoTipo))
    status: Mapped[MovimientoEstado] = mapped_column(
        "status", SAEnum(MovimientoEstado), default=MovimientoEstado.PENDIENTE
    )
    concept: Mapped[str] = mapped_column("concept", String)
    reference: Mapped[str | None] = mapped_column("reference", String, nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(
        "counterparty_name", String, nullable=True
    )
    counterparty_iban: Mapped[str | None] = mapped_column(
        "counterparty_iban", String, nullable=True
    )
    counterparty_bank: Mapped[str | None] = mapped_column(
        "counterparty_bank", String, nullable=True
    )
    commission: Mapped[float] = mapped_column("commission", default=0)
    source: Mapped[str] = mapped_column("source", String, default="ocr")
    attachment_url: Mapped[str | None] = mapped_column("attachment_url", String, nullable=True)
    sepa_end_to_end_id: Mapped[str | None] = mapped_column(
        "sepa_end_to_end_id", String, nullable=True
    )
    sepa_creditor_id: Mapped[str | None] = mapped_column("sepa_creditor_id", String, nullable=True)
    sepa_mandate_ref: Mapped[str | None] = mapped_column("sepa_mandate_ref", String, nullable=True)
    sepa_scheme: Mapped[str | None] = mapped_column("sepa_scheme", String, nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        "customer_id", UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    category: Mapped[str | None] = mapped_column("category", String(100), nullable=True)
    origin: Mapped[str | None] = mapped_column("origin", String(100), nullable=True)

    # Relationships
    account: Mapped[BankAccount] = relationship(BankAccount)
    customer: Mapped[Client | None] = relationship(Client)


class Payment(Base):
    """Payment model."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        "tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    bank_tx_id: Mapped[uuid.UUID] = mapped_column(
        "bank_tx_id", UUID(as_uuid=True), ForeignKey("bank_transactions.id"), index=True
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        "invoice_id", UUID(as_uuid=True), ForeignKey("invoices.id"), index=True
    )
    date: Mapped[date] = mapped_column(Date())
    applied_amount: Mapped[float] = mapped_column("applied_amount")
    notes: Mapped[str] = mapped_column("notes", String, nullable=True)

    # Relationships
    bank_tx: Mapped[BankTransaction] = relationship(BankTransaction)
    invoice: Mapped[Invoice] = relationship(Invoice)


class InternalTransfer(Base):
    """Internal transfer between accounts model."""

    __tablename__ = "internal_transfers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        "tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    source_tx_id: Mapped[uuid.UUID] = mapped_column(
        "source_tx_id", UUID(as_uuid=True), ForeignKey("bank_transactions.id")
    )
    destination_tx_id: Mapped[uuid.UUID] = mapped_column(
        "destination_tx_id", UUID(as_uuid=True), ForeignKey("bank_transactions.id")
    )
    exchange_rate: Mapped[float] = mapped_column("exchange_rate", default=1.0)
