"""Payment Slip (Boleto/Nómina) Model"""

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_table_args, schema_column

# Enums
payslip_status = SQLEnum(
    "GENERATED",
    "SENT",
    "VIEWED",
    "ARCHIVED",
    name="payslip_status",
    create_type=False,
)


class PaymentSlip(Base):
    """
    Boleta/Nómina digital (comprobante de pago).
    
    Attributes:
        payroll_detail_id: Detalle de nómina
        employee_id: Empleado
        pdf_content: PDF del boleto (binario)
        xml_content: XML del boleto (opcional)
        access_token: Token para acceso seguro
        status: GENERATED, SENT, VIEWED, ARCHIVED
        sent_at: Fecha de envío
        viewed_at: Fecha de visualización
        valid_until: Fecha de caducidad de acceso
    """
    
    __tablename__ = "payment_slips"
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
    
    # References
    payroll_detail_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("payroll_details"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("employees"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # Content
    pdf_content: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True,
        comment="PDF del boleto"
    )
    xml_content: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="XML del boleto (opcional)"
    )
    
    # Access control
    access_token: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Token para acceso seguro"
    )
    valid_until: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Fecha hasta la cual el acceso es válido"
    )
    
    # Status and dates
    status: Mapped[str] = mapped_column(
        payslip_status, nullable=False, default="GENERATED",
        comment="GENERATED, SENT, VIEWED, ARCHIVED"
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
        comment="Fecha de envío por email"
    )
    viewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
        comment="Fecha de primera visualización"
    )
    
    # Download tracking
    download_count: Mapped[int] = mapped_column(
        nullable=False, default=0,
        comment="Número de descargas"
    )
    last_download_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
        comment="Última descarga"
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
