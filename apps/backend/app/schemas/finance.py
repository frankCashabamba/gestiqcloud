"""Finance schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TransactionStatus = Literal["pending", "cleared", "reconciled", "cancelled"]


class FinanceMovementBase(BaseModel):
    date: date = Field(default_factory=date.today)
    cheque_number: str | None = Field(None, max_length=50)
    status: TransactionStatus = Field(default="pending")


class FinanceMovementCreate(FinanceMovementBase):
    pass


class FinanceMovementUpdate(BaseModel):
    date: date | None = None
    cheque_number: str | None = Field(None, max_length=50)
    status: TransactionStatus | None = None

    model_config = ConfigDict(extra="forbid")


class FinanceMovementResponse(FinanceMovementBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
