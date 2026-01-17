"""
Accounting Models - Sistema de Contabilidad

Sistema completo de contabilidad general con:
- Plan de cuentas jerárquico (PGC España + Ecuador)
- Asientos contables (libro diario)
- Mayor contable
- Balance y P&L automáticos

Multi-moneda y multi-país.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import TIMESTAMP, Boolean, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

# Enums
account_type = SQLEnum(
    "ASSET",  # Assets
    "LIABILITY",  # Liabilities
    "EQUITY",  # Equity
    "INCOME",  # Income
    "EXPENSE",  # Expenses
    name="account_type",
    create_type=False,
)

entry_status = SQLEnum(
    "DRAFT",  # Not validated
    "VALIDATED",  # Validated (debit = credit)
    "POSTED",  # Posted
    "CANCELLED",  # Cancelled
    name="entry_status",
    create_type=False,
)


class ChartOfAccounts(Base):
    """
    Chart of Accounts - Catalog of ledger accounts.

    Hierarchical structure:
    - Level 1: Groups (1, 2, 3, 4, 5, 6, 7)
    - Level 2: Subgroups (10, 11, 12, ...)
    - Level 3: Accounts (100, 101, 102, ...)
    - Level 4: Sub-accounts (1000, 1001, ...)

    Attributes:
        code: Account code (e.g., 5700001)
        name: Account name
        type: ASSET, LIABILITY, EQUITY, INCOME, EXPENSE
        level: Hierarchical level (1-4)
        parent_id: ID of parent account (for hierarchy)
        can_post: If allows direct movements (sub-accounts)
        active: If the account is active
    """

    __tablename__ = "chart_of_accounts"
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

    # Code and name
    code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="Account code (e.g., 5700001)"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Account name")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    type: Mapped[str] = mapped_column(
        account_type,
        nullable=False,
        index=True,
        comment="ASSET, LIABILITY, EQUITY, INCOME, EXPENSE",
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="Hierarchical level (1-4)")

    # Hierarchy
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("chart_of_accounts"), ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID of parent account",
    )

    # Configuration
    can_post: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="If allows direct movements (True for sub-accounts)",
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Balances (calculated)
    debit_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Accumulated debit balance"
    )
    credit_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Accumulated credit balance"
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Net balance (debit - credit)"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations (self-referential)
    children: Mapped[list["ChartOfAccounts"]] = relationship(
        "ChartOfAccounts",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="ChartOfAccounts.parent_id",
        lazy="selectin",
    )
    parent: Mapped[Optional["ChartOfAccounts"]] = relationship(
        "ChartOfAccounts",
        back_populates="children",
        foreign_keys=[parent_id],
        remote_side=[id],
        lazy="select",
    )


class JournalEntry(Base):
    """
    Journal Entry - Daily journal record.

    Attributes:
        number: Unique entry number (e.g., JE-2025-0001)
        date: Entry date
        type: OPENING, OPERATIONS, REGULARIZATION, CLOSING
        description: Entry description
        status: DRAFT, VALIDATED, POSTED, CANCELLED
        debit_total: Total debit sum
        credit_total: Total credit sum
        is_balanced: True if debit = credit
    """

    __tablename__ = "journal_entries"
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

    # Numbering
    number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True, comment="Unique number (JE-YYYY-NNNN)"
    )

    # Date and type
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="Entry date")
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="OPENING, OPERATIONS, REGULARIZATION, CLOSING",
    )

    # Description
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="Entry description")

    # Totals
    debit_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total debit sum"
    )
    credit_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Total credit sum"
    )
    is_balanced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="True if debit = credit"
    )

    # Status
    status: Mapped[str] = mapped_column(entry_status, nullable=False, index=True)

    # Reference to source document
    ref_doc_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Source document type (invoice, payment, etc.)"
    )
    ref_doc_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relations
    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine", back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )


class JournalEntryLine(Base):
    """
    Journal Entry Line - Individual movement (debit or credit).

    Attributes:
        entry_id: ID of parent entry
        account_id: ID of ledger account
        debit: Debit amount
        credit: Credit amount
        description: Line description
        line_number: Order within the entry
    """

    __tablename__ = "journal_entry_lines"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # References
    entry_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("journal_entries"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("chart_of_accounts"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Amounts (only one should have value, the other at 0)
    debit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Debit amount"
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Credit amount"
    )

    # Description
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Order
    line_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Order within the entry"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relations
    entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry", back_populates="lines", lazy="select"
    )
    account: Mapped["ChartOfAccounts"] = relationship(
        "ChartOfAccounts", foreign_keys=[account_id], lazy="select"
    )
