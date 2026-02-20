"""Domain models for reconciliation module."""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.config.database import Base


class ReconciliationBankStatement(Base):
    """Imported bank statement."""
    __tablename__ = "bank_statements"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    bank_name = Column(String(200), nullable=False)
    account_number = Column(String(50), nullable=False)
    statement_date = Column(Date, nullable=False)
    file_name = Column(String(255), nullable=True)
    import_format = Column(String(20), nullable=False, default="manual")
    status = Column(String(20), nullable=False, default="imported")
    total_transactions = Column(Integer, nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    unmatched_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lines = relationship(
        "ReconciliationStatementLine",
        back_populates="statement",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<BankStatement {self.id}: {self.bank_name} {self.statement_date}>"


class ReconciliationStatementLine(Base):
    """Single transaction line within a bank statement."""
    __tablename__ = "statement_lines"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID, ForeignKey("bank_statements.id"), nullable=False, index=True)
    tenant_id = Column(UUID, nullable=False, index=True)
    transaction_date = Column(Date, nullable=False)
    description = Column(String(500), nullable=False)
    reference = Column(String(200), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    balance = Column(Numeric(15, 2), nullable=True)
    transaction_type = Column(String(20), nullable=False)
    matched_invoice_id = Column(UUID, nullable=True)
    match_status = Column(String(20), nullable=False, default="unmatched")
    match_confidence = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    statement = relationship(ReconciliationBankStatement, back_populates="lines")

    def __repr__(self):
        return f"<StatementLine {self.id}: {self.description} {self.amount}>"
