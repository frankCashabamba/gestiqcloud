"""Payroll & Payroll Detail Models"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

# Enums
payroll_status = SQLEnum(
    "DRAFT",
    "CONFIRMED",
    "PAID",
    "CANCELLED",
    name="payroll_status",
    create_type=False,
)


class Payroll(Base):
    """
    Nómina (lote de pagos de salarios).

    Attributes:
        tenant_id: Tenant
        payroll_month: Mes de la nómina (YYYY-MM)
        payroll_date: Fecha de pago
        status: DRAFT, CONFIRMED, PAID, CANCELLED
        total_gross: Total salarios brutos
        total_deductions: Total deducciones
        total_net: Total neto a pagar
        currency: Moneda
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

    # Period
    payroll_month: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True, comment="Mes de la nómina (YYYY-MM format)"
    )
    payroll_date: Mapped[date] = mapped_column(Date, nullable=False, comment="Fecha de pago")

    # Counts
    total_employees: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Total de empleados en la nómina"
    )

    # Totals
    total_gross: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total salarios brutos"
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total deducciones"
    )
    total_net: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total neto = gross - deductions"
    )

    # Breakdown by type
    total_irpf: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total IRPF (España)"
    )
    total_social_security_employee: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total Seguridad Social (empleado)"
    )
    total_social_security_employer: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total Seguridad Social (empleador)"
    )

    # Currency
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    # Status
    status: Mapped[str] = mapped_column(
        payroll_status,
        nullable=False,
        default="DRAFT",
        comment="DRAFT, CONFIRMED, PAID, CANCELLED",
        index=True,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Notas sobre la nómina")

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    details: Mapped[list["PayrollDetail"]] = relationship(
        "PayrollDetail", back_populates="payroll", cascade="all, delete-orphan", lazy="selectin"
    )
    taxes: Mapped[list["PayrollTax"]] = relationship(
        "PayrollTax", back_populates="payroll", cascade="all, delete-orphan", lazy="selectin"
    )


class PayrollDetail(Base):
    """
    Detalle de un empleado en la nómina.

    Attributes:
        payroll_id: Nómina padre
        employee_id: Empleado
        gross_salary: Salario bruto
        irpf: Impuesto sobre la renta (España)
        social_security: Aportación Seguridad Social (empleado)
        deductions: Otras deducciones
        net_salary: Neto = gross - irpf - SS - deductions
    """

    __tablename__ = "payroll_details"
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
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("employees"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Salary
    gross_salary: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Salario bruto"
    )

    # Deductions breakdown
    irpf: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="IRPF (España)"
    )
    social_security: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Aportación Seguridad Social (empleado)"
    )
    mutual_insurance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Seguro mutualista"
    )
    other_deductions: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Otras deducciones"
    )

    # Totals
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total deducciones"
    )
    net_salary: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Neto = gross - total_deductions"
    )

    # Currency
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    # Notes
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    payroll: Mapped["Payroll"] = relationship("Payroll", back_populates="details", lazy="select")


class PayrollTax(Base):
    """
    Resumen de impuestos y aportes de la nómina.

    Attributes:
        payroll_id: Nómina padre
        tax_type: Tipo de impuesto (IRPF, SOCIAL_SECURITY_EMPLOYEE, SOCIAL_SECURITY_EMPLOYER, etc)
        total_amount: Monto total del impuesto
    """

    __tablename__ = "payroll_taxes"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    payroll_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("payrolls"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tax info
    tax_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="IRPF, SOCIAL_SECURITY_EMPLOYEE, SOCIAL_SECURITY_EMPLOYER, MUTUAL_INSURANCE",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Monto total del impuesto/aporte"
    )

    # Currency
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    # Notes
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    payroll: Mapped["Payroll"] = relationship("Payroll", back_populates="taxes", lazy="select")
