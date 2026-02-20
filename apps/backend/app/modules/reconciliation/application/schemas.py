"""Pydantic schemas for reconciliation module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionItem(BaseModel):
    """Single transaction within a bank statement import."""

    transaction_date: date
    description: str
    reference: str | None = None
    amount: Decimal
    transaction_type: str = Field(..., pattern="^(credit|debit)$")


class ImportStatementRequest(BaseModel):
    """Request to import a bank statement."""

    bank_name: str
    account_number: str
    statement_date: date
    transactions: list[TransactionItem]

    class Config:
        json_schema_extra = {
            "example": {
                "bank_name": "Banco Pichincha",
                "account_number": "2200123456",
                "statement_date": "2025-01-31",
                "transactions": [
                    {
                        "transaction_date": "2025-01-15",
                        "description": "Transfer from client ABC",
                        "reference": "INV-2025-001",
                        "amount": 1500.00,
                        "transaction_type": "credit",
                    }
                ],
            }
        }


class StatementResponse(BaseModel):
    """Response containing bank statement details."""

    id: UUID
    bank_name: str
    account_number: str
    statement_date: date
    status: str
    total_transactions: int
    matched_count: int
    unmatched_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class StatementListResponse(BaseModel):
    """Paginated list of bank statements."""

    items: list[StatementResponse]
    total: int
    skip: int
    limit: int


class StatementLineResponse(BaseModel):
    """Response containing a statement line."""

    id: UUID
    transaction_date: date
    description: str
    reference: str | None = None
    amount: Decimal
    transaction_type: str
    match_status: str
    match_confidence: Decimal | None = None
    matched_invoice_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ManualMatchRequest(BaseModel):
    """Request to manually match a statement line to an invoice."""

    line_id: UUID
    invoice_id: UUID


class ReconciliationSummaryResponse(BaseModel):
    """Aggregated reconciliation statistics."""

    total_statements: int
    total_lines: int
    matched: int
    unmatched: int
    auto_matched: int
    manual_matched: int


class ReconcilePaymentRequest(BaseModel):
    """Request to reconcile a payment against an invoice."""

    invoice_id: UUID
    payment_amount: Decimal
    payment_date: datetime
    payment_reference: str
    payment_method: str = "bank_transfer"
    notes: str | None = None


class ReconcilePaymentResponse(BaseModel):
    """Response after reconciling a payment."""

    success: bool
    payment_id: str | None = None
    invoice_number: str | None = None
    amount_paid: float | None = None
    remaining_balance: float | None = None
    payment_status: str | None = None
    invoice_status: str | None = None
