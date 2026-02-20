"""E-Invoicing Country Settings & Configuration"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, TIMESTAMP, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, schema_table_args


class TaxRegime(Base):
    """
    Régimen fiscal (no configurable por tenant, es master data).

    Attributes:
        country: País (ES, EC, MX, CL, CO)
        regime_code: Código del régimen
        regime_name: Nombre del régimen
        description: Descripción
        requires_ruc: Si requiere RUC
        vat_applicable: Si aplica IVA
    """

    __tablename__ = "tax_regimes"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Country
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, index=True, comment="País (ES, EC, MX, CL, CO)"
    )

    # Regime
    regime_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Código del régimen"
    )
    regime_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Nombre del régimen"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Descripción")

    # Requirements
    requires_ruc: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Si requiere RUC"
    )
    requires_invoice_authorization: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Si requiere autorización SRI/Autoridad"
    )
    vat_applicable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Si aplica IVA"
    )

    # VAT rates (JSON)
    vat_rates: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Tasas de IVA por categoría (JSON)"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )


class EInvoicingCountrySettings(Base):
    """
    Configuración de facturación electrónica por país/tenant.

    Attributes:
        tenant_id: Tenant
        country: País (ES, EC, MX, CL, CO)
        is_enabled: Si está habilitada la e-invoicing
        environment: STAGING, PRODUCTION
        api_endpoint: URL del endpoint (desde tabla, no hardcodeado)
        certificate_path: Ruta al certificado (si aplica)
        certificate_password: Contraseña cifrada
        username: Usuario para autenticación
        password: Contraseña cifrada
    """

    __tablename__ = "einvoicing_country_settings"
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

    # Country
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, index=True, comment="País (ES, EC, MX, CL, CO)"
    )

    # Enable/Disable
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Si está habilitada la e-invoicing para este país",
    )

    # Environment
    environment: Mapped[str] = mapped_column(
        String(20), nullable=False, default="STAGING", comment="STAGING, PRODUCTION"
    )

    # API Configuration (from database, not hardcoded)
    api_endpoint: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL del endpoint (configurable por país/tenant)"
    )

    # Certificate/Authentication (encrypted)
    certificate_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="ID del archivo certificado (si aplica)"
    )
    certificate_password_encrypted: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Contraseña cifrada del certificado"
    )

    # Credentials (encrypted)
    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Usuario para autenticación"
    )
    password_encrypted: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Contraseña cifrada"
    )
    api_key_encrypted: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="API key cifrada (si aplica)"
    )

    # Validation rules (JSON)
    validation_rules: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Reglas de validación específicas del país (JSON)"
    )

    # Retry policy
    max_retries: Mapped[int] = mapped_column(
        nullable=False, default=5, comment="Máximo número de reintentos"
    )
    retry_backoff_seconds: Mapped[int] = mapped_column(
        nullable=False, default=300, comment="Segundos iniciales para exponential backoff"
    )

    # Audit
    configured_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    configured_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )
