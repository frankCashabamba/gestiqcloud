from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PurchaseBase(BaseModel):
    date: date
    total: float
    supplier_id: UUID | None = None
    status: str | None = None


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseUpdate(PurchaseBase):
    pass


class PurchaseOut(PurchaseBase):
    id: UUID
    number: str | None = None
    subtotal: float | None = None
    taxes: float | None = None
    notes: str | None = None
    supplier_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
