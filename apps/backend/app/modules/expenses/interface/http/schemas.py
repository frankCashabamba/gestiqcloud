from datetime import date

from pydantic import BaseModel, ConfigDict


class ExpenseBase(BaseModel):
    date: date
    amount: float
    supplier_id: int | None = None
    concept: str | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass


class ExpenseOut(ExpenseBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
