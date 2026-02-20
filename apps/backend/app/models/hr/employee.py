"""
HR Module - Employee & Salary Models

Models:
  - Employee: Core employee information with personal and employment details
  - EmployeeSalary: Salary configuration with effective dates for history tracking
  - EmployeeDeduction: Configurable deductions/deductions per employee

Related Tables (see migrations):
  - employee_statuses: Dynamic status codes (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, ...)
  - contract_types: Dynamic contract type codes (PERMANENT, TEMPORARY, PART_TIME, ...)
  - deduction_types: Dynamic deduction codes (INCOME_TAX, SOCIAL_SECURITY, HEALTH_INSURANCE, ...)
  - gender_types: Dynamic gender options (MALE, FEMALE, OTHER, PREFER_NOT_TO_SAY, ...)
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

# Database enums (minimal, for backward compatibility)
# Note: These will be gradually replaced by table-driven lookups
employee_status = SQLEnum(
    "ACTIVE",
    "INACTIVE",
    "ON_LEAVE",
    "TERMINATED",
    name="employee_status",
    create_type=False,
)

contract_type = SQLEnum(
    "PERMANENT",
    "TEMPORARY",
    "PART_TIME",
    "APPRENTICE",
    "CONTRACTOR",
    name="contract_type",
    create_type=False,
)

gender = SQLEnum(
    "MALE",
    "FEMALE",
    "OTHER",
    name="gender",
    create_type=False,
)


class Employee(Base):
    """
    Employee record — core HR information.

    Attributes:
        tenant_id: Tenant (company/organization)
        first_name: Employee first name
        last_name: Employee last name
        national_id: National ID / Document (DNI, RUC, Passport, etc)
        email: Employee email
        phone: Contact phone number
        birth_date: Date of birth
        gender: Gender code (M/F/O/etc from employee_statuses table)
        contract_type: Contract type code (PERMANENT, TEMPORARY, etc)
        status: Employment status (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, etc)
        hire_date: Hiring date
        termination_date: Optional termination date
        department: Department name/code
        job_title: Job title/position
        bank_account: Bank account for salary deposits
        bank_name: Bank name
        country: Country code (ISO 3166-1 alpha-2: ES, EC, etc)
        tax_id_secondary: Secondary tax identifier (varies by country)
        notes: Additional notes about employee

    Relations:
        salaries: Historical salary configurations
        deductions: Configured deductions/bonuses
    """

    __tablename__ = "employees"
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

    # Personal info
    first_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Employee first name"
    )
    last_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Employee last name"
    )
    national_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="National ID (unique per tenant, DNI/RUC/Passport)",
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Work email address"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Contact phone number"
    )
    birth_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Date of birth (YYYY-MM-DD)"
    )
    gender: Mapped[str | None] = mapped_column(
        gender, nullable=True, comment="Gender code: MALE, FEMALE, OTHER (from gender_types table)"
    )

    # Employment info
    contract_type: Mapped[str] = mapped_column(
        contract_type,
        nullable=False,
        default="PERMANENT",
        comment="Contract type: PERMANENT, TEMPORARY, PART_TIME, APPRENTICE, CONTRACTOR (from contract_types table)",
    )
    status: Mapped[str] = mapped_column(
        employee_status,
        nullable=False,
        default="ACTIVE",
        comment="Employment status: ACTIVE, INACTIVE, ON_LEAVE, TERMINATED (from employee_statuses table)",
        index=True,
    )

    # Employment dates
    hire_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Employment start date (YYYY-MM-DD)"
    )
    termination_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Employment end date (YYYY-MM-DD), if applicable"
    )

    # Organization info
    department: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Department name or code"
    )
    job_title: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Job title or position"
    )

    # Financial info
    bank_account: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Bank account number for salary deposits"
    )
    bank_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Bank institution name"
    )

    # Localization (by country)
    country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="ES",
        comment="Country code (ISO 3166-1 alpha-2: ES, EC, CO, etc)",
    )
    tax_id_secondary: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Secondary tax identifier (e.g., IRPF code in Spain)"
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional employee notes or comments"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    salaries: Mapped[list["EmployeeSalary"]] = relationship(
        "EmployeeSalary", back_populates="employee", cascade="all, delete-orphan", lazy="selectin"
    )
    deductions: Mapped[list["EmployeeDeduction"]] = relationship(
        "EmployeeDeduction",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class EmployeeSalary(Base):
    """
    Salary configuration — tracks salary history with effective dates.

    Attributes:
        employee_id: Reference to employee
        salary_amount: Gross monthly salary
        effective_date: Date when salary becomes/became active
        end_date: Optional date when salary ended (if changed later)
        currency: Currency code (ISO 4217: EUR, USD, etc)
        notes: Change notes or comments
        created_by: User who created this salary record
        created_at: Record creation timestamp

    Purpose:
        Maintains salary history for the employee, supporting:
        - Historical salary lookups (retroactive payroll)
        - Salary change tracking
        - Period-specific salary audits
    """

    __tablename__ = "employee_salaries"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("employees"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Salary details
    salary_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="Gross monthly salary amount"
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
        comment="Currency code (ISO 4217: EUR, USD, GBP, etc)",
    )

    # Effective period
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date when salary becomes/became active (YYYY-MM-DD)",
    )
    end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Date when salary ended (YYYY-MM-DD), if changed later"
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Change notes (reason, approval ref, etc)"
    )

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    employee: Mapped["Employee"] = relationship(
        "Employee", back_populates="salaries", lazy="select"
    )


class EmployeeDeduction(Base):
    """
    Employee deductions/bonuses — taxes, insurance, benefits, etc.

    Supports both percentage-based and fixed-amount deductions with effective dates.

    Attributes:
        employee_id: Reference to employee
        deduction_type: Type code (INCOME_TAX, SOCIAL_SECURITY, HEALTH_INSURANCE, LOAN_PAYMENT, etc)
        percentage: Deduction percentage (if percentage-based, e.g., 15.5)
        fixed_amount: Fixed deduction amount (if not percentage-based)
        effective_date: Date when deduction becomes/became active
        end_date: Optional date when deduction ended
        notes: Deduction description or comments
        created_at: Record creation timestamp

    Purpose:
        Tracks employee-specific deductions for payroll processing:
        - Mandatory deductions (income tax, social security)
        - Optional deductions (health insurance, loan repayment)
        - Company bonuses/additions (allowances, benefits)

    Note:
        Deduction types are managed in the deduction_types lookup table
        for multi-tenant and configurable behavior.
    """

    __tablename__ = "employee_deductions"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reference
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("employees"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Deduction details
    deduction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Deduction type code: INCOME_TAX, SOCIAL_SECURITY, HEALTH_INSURANCE, LOAN_PAYMENT, etc (from deduction_types table)",
    )
    percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage amount (if percentage-based deduction, e.g., 15.5)",
    )
    fixed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True, comment="Fixed amount (if fixed-amount deduction)"
    )

    # Effective period
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date when deduction becomes/became active (YYYY-MM-DD)",
    )
    end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="Date when deduction ended (YYYY-MM-DD), if applicable"
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Deduction description, reason, or comments"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    employee: Mapped["Employee"] = relationship(
        "Employee", back_populates="deductions", lazy="select"
    )
