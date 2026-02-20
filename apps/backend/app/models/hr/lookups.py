"""HR Lookup Tables - Database-driven enumerations"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, schema_table_args


class EmployeeStatus(Base):
    """Employee status lookup table - replaces hardcoded enum"""

    __tablename__ = "employee_statuses"
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
    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Status code: ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, RETIRED"
    )
    name_en: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="English name"
    )
    name_es: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Spanish name"
    )
    name_pt: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Portuguese name"
    )
    color_code: Mapped[str | None] = mapped_column(
        String(7), nullable=True,
        comment="Hex color for UI (e.g., #22c55e)"
    )
    icon_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Icon code for UI (e.g., check-circle)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True,
        comment="Whether status is available"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Display sort order"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_employee_status_per_tenant"),
        schema_table_args(),
    )


class ContractType(Base):
    """Contract type lookup table - replaces hardcoded enum"""

    __tablename__ = "contract_types"
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
    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Contract type code"
    )
    name_en: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="English name"
    )
    name_es: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Spanish name"
    )
    name_pt: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Portuguese name"
    )
    is_permanent: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="Is permanent (indefinite) contract"
    )
    full_time: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="Is full-time contract"
    )
    notice_period_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Notice period in days"
    )
    probation_months: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Probation period in months"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True,
        comment="Whether type is available"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Display sort order"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_contract_type_per_tenant"),
        schema_table_args(),
    )


class DeductionType(Base):
    """Deduction/bonus type lookup table"""

    __tablename__ = "deduction_types"
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
    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Deduction type code"
    )
    name_en: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="English name"
    )
    name_es: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Spanish name"
    )
    name_pt: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Portuguese name"
    )
    is_deduction: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="TRUE=deduction, FALSE=bonus"
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="Is mandatory deduction"
    )
    is_percentage_based: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="Can be applied as percentage"
    )
    is_fixed_amount: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="Can be applied as fixed amount"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True,
        comment="Whether type is available"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Display sort order"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_deduction_type_per_tenant"),
        schema_table_args(),
    )


class GenderType(Base):
    """Gender type lookup table - replaces hardcoded enum"""

    __tablename__ = "gender_types"
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
    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Gender code"
    )
    name_en: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="English name"
    )
    name_es: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Spanish name"
    )
    name_pt: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Portuguese name"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True,
        comment="Whether type is available"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Display sort order"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_gender_type_per_tenant"),
        schema_table_args(),
    )


class DocumentIDType(Base):
    """Document/ID type lookup table - for POS and employee identification"""

    __tablename__ = "document_id_types"
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
    country_code: Mapped[str] = mapped_column(
        String(2), nullable=False,
        comment="Country code (ISO 3166-1 alpha-2: EC, ES, CO, etc)"
    )
    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="ID type code: CEDULA, RUC, PASSPORT, DNI, etc"
    )
    name_en: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="English name"
    )
    name_es: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Spanish name"
    )
    name_pt: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Portuguese name"
    )
    regex_pattern: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Regex pattern for validation (e.g., ^\\d{10}$ for 10 digits)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True,
        comment="Whether ID type is available"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Display sort order"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default="now()", onupdate=datetime.utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "country_code", "code", name="uq_document_id_type_per_tenant"),
        schema_table_args(),
    )
