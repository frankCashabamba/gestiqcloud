"""Expenses Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExpenseBase(BaseModel):
    """Common expense fields."""

    number: str = Field(..., alias="numero", max_length=50, description="Expense number")
    supplier_id: UUID | None = Field(None, description="Supplier ID")
    expense_category_id: UUID | None = Field(None, description="Expense category ID")
    date: date = Field(default_factory=date.today, alias="fecha")
    concept: str = Field(..., alias="concepto", max_length=255, description="Expense concept")
    subtotal: float = Field(default=0, ge=0)
    taxes: float = Field(default=0, ge=0, alias="impuestos")
    total: float = Field(default=0, ge=0)
    status: str = Field(
        default="draft", alias="estado", pattern="^(draft|approved|paid|cancelled)$"
    )
    payment_method: str | None = Field(
        None, alias="metodo_pago", pattern="^(cash|card|transfer|check)$"
    )
    reference: str | None = Field(
        None, alias="referencia", max_length=100, description="Bank/cheque reference"
    )
    notes: str | None = Field(None, alias="notas")

    model_config = ConfigDict(populate_by_name=True)


class ExpenseCreate(ExpenseBase):
    """Create expense."""


class ExpenseUpdate(BaseModel):
    """Update expense (all fields optional)."""

    number: str | None = Field(None, alias="numero", max_length=50)
    supplier_id: UUID | None = Field(None)
    expense_category_id: UUID | None = Field(None)
    date: date | None = Field(None, alias="fecha")
    concept: str | None = Field(None, alias="concepto", max_length=255)
    subtotal: float | None = Field(None, ge=0)
    taxes: float | None = Field(None, alias="impuestos", ge=0)
    total: float | None = Field(None, ge=0)
    status: str | None = Field(None, alias="estado", pattern="^(draft|approved|paid|cancelled)$")
    payment_method: str | None = Field(
        None, alias="metodo_pago", pattern="^(cash|card|transfer|check)$"
    )
    reference: str | None = Field(None, alias="referencia", max_length=100)
    notes: str | None = Field(None, alias="notas")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExpenseResponse(ExpenseBase):
    """Expense response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID = Field(alias="usuario_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseList(BaseModel):
    """Paginated expense list."""

    items: list[ExpenseResponse]
    total: int
    page: int = 1
    page_size: int = 100
