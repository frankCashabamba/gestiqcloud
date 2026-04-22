from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ExpenseBase(BaseModel):
    date: date
    amount: float
    supplier_id: UUID | None = None
    concept: str | None = None
    category: str | None = None
    subcategory: str | None = None
    payment_method: str | None = None
    invoice_number: str | None = None
    status: str | None = None
    notes: str | None = None

    @field_validator("supplier_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass


class ExpenseOut(ExpenseBase):
    id: UUID
    vat: float | None = None
    total: float | None = None
    paid_amount: float | None = None
    pending_amount: float | None = None

    model_config = ConfigDict(from_attributes=True)
