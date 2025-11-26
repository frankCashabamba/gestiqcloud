"""
Payroll Models - Sistema de Nóminas y Gestión Salarial

Sistema completo de cálculo de nóminas con:
- Conceptos salariales configurables (base, complementos, deducciones)
- Cálculo automático de impuestos y seguridad social
- Compatibilidad España (IRPF, Seg. Social) y Ecuador (IESS, IR)
- Generación de recibos de nómina
- Histórico y auditoría completa

Multi-país y multi-sector.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from app.config.database import Base, schema_column, schema_table_args
from sqlalchemy import JSON, TIMESTAMP, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


# Enums
payroll_status = SQLEnum(
    "DRAFT",  # Borrador (calculada, no aprobada)
    "APPROVED",  # Aprobada (lista para pago)
    "PAID",  # Pagada
    "CANCELLED",  # Cancelada
    name="payroll_status",
    create_type=False,
)

payroll_type = SQLEnum(
    "MONTHLY",  # Nómina mensual ordinaria
    "BONUS",  # Paga extra
    "SEVERANCE",  # Liquidación final
    "SPECIAL",  # Pagos especiales
    name="payroll_type",
    create_type=False,
)


class Payroll(Base):
    """
    Payroll - Employee salary receipt for a period.

    Attributes:
        number: Unique payroll number (e.g.: PAY-2025-11-0001)
        employee_id: Employee it belongs to
        period_month: Period month (1-12)
        period_year: Period year
        type: Payroll type (MONTHLY, EXTRA, FINAL, SPECIAL)

        Devengos (positivos):
        - salario_base: Salario base del período
        - complementos: Suma de complementos salariales
        - horas_extra: Pago por horas extra
        - otros_devengos: Otros conceptos positivos
        - total_devengado: Suma total de devengos

        Deducciones (negativas):
        - seg_social: Cotización seguridad social (España) o IESS (Ecuador)
        - irpf: Retención IRPF (España) o IR (Ecuador)
        - otras_deducciones: Otros conceptos negativos
        - total_deducido: Suma total de deducciones

        Totales:
        - liquido_total: Total a pagar (devengos - deducciones)

        Estado y pago:
        - status: DRAFT, APPROVED, PAID, CANCELLED
        - fecha_pago: Fecha real de pago
        - metodo_pago: efectivo, transferencia, etc.
    """

    __tablename__ = "payrolls"
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

    # Numeración
    number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Número único (NOM-YYYY-MM-NNNN)",
    )

    # Referencias
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Período
    period_month: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Period month (1-12)"
    )
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, comment="Period year")
    type: Mapped[str] = mapped_column(
        payroll_type, nullable=False, default="MONTHLY", comment="Payroll type"
    )

    # === EARNINGS (positive) ===
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Base salary for period"
    )
    allowances: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Sum of salary allowances"
    )
    overtime: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Overtime payment"
    )
    other_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Other earnings"
    )
    total_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Total earnings (sum of earnings)"
    )

    # === DEDUCTIONS (negative) ===
    social_security: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Social Security (ES) or IESS (EC)"
    )
    income_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Income Tax (ES) or IR (EC)"
    )
    other_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Other deductions"
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Total deductions (sum of deductions)"
    )

    # === TOTALES ===
    net_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Net amount to pay (earnings - deductions)",
    )

    # === PAGO ===
    payment_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Actual payment date"
    )
    payment_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="cash, transfer, etc."
    )

    # === ESTADO ===
    status: Mapped[str] = mapped_column(payroll_status, nullable=False, default="DRAFT", index=True)

    # === INFORMACIÓN ADICIONAL ===
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    concepts_json: Mapped[dict | None] = mapped_column(
        JSON_TYPE, nullable=True, comment="Detail of concepts (allowances, deductions)"
    )

    # === AUDITORÍA ===
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # === RELACIONES ===
    concepts: Mapped[list["PayrollConcept"]] = relationship(
        "PayrollConcept", back_populates="payroll", cascade="all, delete-orphan", lazy="selectin"
    )


class PayrollConcept(Base):
    """
    Payroll Concept - Individual line for earning or deduction.

    Allows breaking down amounts into specific concepts:
    - Earnings: transport allowance, night shift bonus, seniority, etc.
    - Deductions: advances, garnishments, loans, etc.

    Attributes:
        type: 'EARNING' or 'DEDUCTION'
        code: Concept code (e.g.: PLUS_TRANS, ADVANCE)
        description: Readable description
        amount: Concept amount (always positive)
        is_base: Whether it counts towards contribution base
    """

    __tablename__ = "payroll_concepts"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # References
    payroll_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("payrolls"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Type
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="EARNING or DEDUCTION")
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="Concept code")
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="Concept amount (always positive)"
    )

    # Configuration
    is_base: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Whether it counts towards contribution base"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    payroll: Mapped["Payroll"] = relationship("Payroll", back_populates="concepts", lazy="select")


class PayrollTemplate(Base):
    """
    Payroll Template - Configuration of standard concepts per employee.

    Allows defining fixed concepts that are automatically applied
    each month (e.g.: transport allowance, night shift bonus, etc.)

    Attributes:
        employee_id: Employee it applies to
        concepts_json: List of concepts with type, code, description, amount
        active: Whether the template is active
    """

    __tablename__ = "payroll_templates"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Template name")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configured concepts
    concepts_json: Mapped[dict] = mapped_column(
        JSON_TYPE, nullable=False, comment="List of standard concepts"
    )

    active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )
