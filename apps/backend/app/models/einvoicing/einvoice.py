"""E-Invoice & Digital Signature Models"""

import uuid
from datetime import date, datetime

from sqlalchemy import TIMESTAMP, Boolean, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

# Enums
einvoice_status = SQLEnum(
    "PENDING",
    "SENDING",
    "SENT",
    "ACCEPTED",
    "REJECTED",
    "ERROR",
    "RETRY",
    name="einvoice_status",
    create_type=False,
)

signature_status = SQLEnum(
    "NOT_SIGNED",
    "SIGNED",
    "VERIFIED",
    "FAILED",
    name="signature_status",
    create_type=False,
)


class EInvoice(Base):
    """
    Factura electrónica enviada a entidad fiscal.

    Attributes:
        tenant_id: Tenant
        invoice_id: Factura origen
        country: País destino (ES, EC, MX, CL, CO)
        status: PENDING, SENDING, SENT, ACCEPTED, REJECTED, ERROR, RETRY
        xml_content: XML generado
        fiscal_number: Número asignado por autoridad fiscal
        authorization_code: Código de autorización
        sent_at: Fecha de envío
        accepted_at: Fecha de aceptación
    """

    __tablename__ = "einvoices"
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

    # Invoice reference
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="Referencia a factura original",
        index=True,
    )

    # Country and fiscal info
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, index=True, comment="País destino (ES, EC, MX, CL, CO)"
    )
    fiscal_regime: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="STANDARD",
        comment="Régimen fiscal (del tenant o cliente)",
    )

    # XML and content
    xml_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="XML generado")

    # Fiscal identification
    fiscal_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Número asignado por autoridad fiscal (SII, FE, CFDI, etc)",
    )
    authorization_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Código de autorización"
    )
    authorization_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha de autorización"
    )

    # Status
    status: Mapped[str] = mapped_column(
        einvoice_status,
        nullable=False,
        default="PENDING",
        comment="PENDING, SENDING, SENT, ACCEPTED, REJECTED, ERROR, RETRY",
        index=True,
    )

    # Dates
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha de envío"
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha de aceptación"
    )

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(
        nullable=False, default=0, comment="Número de reintentos"
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Próxima fecha de reintento"
    )

    # Notes and errors
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Notas sobre el envío")

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    errors: Mapped[list["EInvoiceError"]] = relationship(
        "EInvoiceError", back_populates="einvoice", cascade="all, delete-orphan", lazy="selectin"
    )
    signature: Mapped["EInvoiceSignature | None"] = relationship(
        "EInvoiceSignature",
        back_populates="einvoice",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class EInvoiceSignature(Base):
    """
    Firma digital de la factura electrónica.

    Attributes:
        einvoice_id: Factura electrónica
        certificate_serial: Número de serie del certificado
        certificate_issuer: Emisor del certificado
        certificate_subject: Sujeto del certificado
        certificate_valid_from: Válido desde
        certificate_valid_to: Válido hasta
        signature_value: Valor de la firma (base64)
        digest_value: Valor del digest (base64)
        status: NOT_SIGNED, SIGNED, VERIFIED, FAILED
    """

    __tablename__ = "einvoice_signatures"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    einvoice_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("einvoices"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Certificate info
    certificate_serial: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Número de serie del certificado"
    )
    certificate_issuer: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Emisor del certificado"
    )
    certificate_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Sujeto del certificado"
    )
    certificate_valid_from: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Fecha de inicio de validez"
    )
    certificate_valid_to: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Fecha de fin de validez"
    )

    # Signature data
    signature_value: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Valor de la firma (base64)"
    )
    digest_value: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Valor del digest"
    )
    digest_algorithm: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SHA256",
        comment="Algoritmo de hash (SHA256, SHA1, etc)",
    )

    # Status
    status: Mapped[str] = mapped_column(
        signature_status,
        nullable=False,
        default="NOT_SIGNED",
        comment="NOT_SIGNED, SIGNED, VERIFIED, FAILED",
    )

    # Verification
    verified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, comment="Fecha de verificación"
    )
    verification_result: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Resultado de la verificación"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    einvoice: Mapped["EInvoice"] = relationship(
        "EInvoice", back_populates="signature", lazy="select"
    )


class EInvoiceStatus(Base):
    """
    Histórico de cambios de estado de la factura electrónica.

    Attributes:
        einvoice_id: Factura electrónica
        old_status: Estado anterior
        new_status: Estado nuevo
        reason: Razón del cambio
        changed_by: Usuario que hizo el cambio
        changed_at: Fecha del cambio
    """

    __tablename__ = "einvoice_statuses"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    einvoice_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("einvoices"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status change
    old_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Estado anterior"
    )
    new_status: Mapped[str] = mapped_column(String(50), nullable=False, comment="Estado nuevo")

    # Reason
    reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Razón del cambio"
    )

    # Audit
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Usuario que hizo el cambio"
    )
    changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )


class EInvoiceError(Base):
    """
    Error ocurrido durante el envío o procesamiento de la factura.

    Attributes:
        einvoice_id: Factura electrónica
        error_code: Código de error
        error_message: Descripción del error
        error_detail: Detalles técnicos
        error_type: VALIDATION, CONNECTIVITY, SIGNATURE, SERVER, OTHER
        recovery_action: Acción recomendada para resolver
        is_recoverable: Si se puede recuperar con reintento
    """

    __tablename__ = "einvoice_errors"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    einvoice_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("einvoices"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Error info
    error_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Código de error"
    )
    error_message: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Descripción del error"
    )
    error_detail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detalles técnicos"
    )
    error_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="VALIDATION, CONNECTIVITY, SIGNATURE, SERVER, OTHER"
    )

    # Recovery
    recovery_action: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Acción recomendada para resolver"
    )
    is_recoverable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Si se puede recuperar con reintento"
    )

    # Audit
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    einvoice: Mapped["EInvoice"] = relationship("EInvoice", back_populates="errors", lazy="select")
