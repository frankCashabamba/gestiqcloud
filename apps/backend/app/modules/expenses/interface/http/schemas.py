from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExpenseBase(BaseModel):
    date: date
    amount: float
    supplier_id: UUID | None = None
    concept: str | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass


class ExpenseOut(ExpenseBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
