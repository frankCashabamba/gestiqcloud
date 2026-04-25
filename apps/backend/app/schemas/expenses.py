"""Expenses Pydantic schemas."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ExpenseStatus = Literal["draft", "approved", "paid", "cancelled"]
PaymentMethod = Literal["cash", "card", "transfer", "check"]


class ExpenseBase(BaseModel):
    """Common expense fields."""

    number: str = Field(..., max_length=50, description="Expense number")
    supplier_id: UUID | None = Field(None, description="Supplier ID")
    expense_category_id: UUID | None = Field(None, description="Expense category ID")
    date: date = Field(default_factory=date.today)
    concept: str = Field(..., max_length=255, description="Expense concept")
    subtotal: float = Field(default=0, ge=0)
    taxes: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    status: ExpenseStatus = Field(default="draft")
    payment_method: PaymentMethod | None = Field(None)
    reference: str | None = Field(None, max_length=100, description="Bank/cheque reference")
    notes: str | None = None

    @field_validator("supplier_id", "expense_category_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v


class ExpenseCreate(ExpenseBase):
    """Create expense."""


class ExpenseUpdate(BaseModel):
    """Update expense (all fields optional)."""

    number: str | None = Field(None, max_length=50)
    supplier_id: UUID | None = Field(None)
    expense_category_id: UUID | None = Field(None)
    date: date | None = None
    concept: str | None = Field(None, max_length=255)
    subtotal: float | None = Field(None, ge=0)
    taxes: float | None = Field(None, ge=0)
    total: float | None = Field(None, ge=0)
    status: ExpenseStatus | None = None
    payment_method: PaymentMethod | None = None
    reference: str | None = Field(None, max_length=100)
    notes: str | None = None

    @field_validator("supplier_id", "expense_category_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v

    model_config = ConfigDict(extra="forbid")


class ExpenseResponse(ExpenseBase):
    """Expense response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseList(BaseModel):
    """Paginated expense list."""

    items: list[ExpenseResponse]
    total: int
    page: int = 1
    page_size: int = 100
