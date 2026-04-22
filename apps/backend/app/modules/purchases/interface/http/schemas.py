from datetime import date as dt_date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurchaseLineCreate(BaseModel):
    product_id: str
    quantity: float
    unit_price: float
    subtotal: float = 0


class PurchaseBase(BaseModel):
    date: dt_date
    total: float = 0
    supplier_id: str | None = None
    supplier_name: str | None = None
    status: str | None = None
    subtotal: float | None = None
    taxes: float | None = None
    notes: str | None = None
    delivery_date: dt_date | None = None


class PurchaseCreate(PurchaseBase):
    lines: list[PurchaseLineCreate] = Field(default_factory=list)


class PurchaseUpdate(BaseModel):
    date: dt_date | None = None
    total: float | None = None
    supplier_id: str | None = None
    status: str | None = None


class PurchaseOut(BaseModel):
    id: UUID
    number: str | None = None
    date: dt_date | None = None
    total: float | None = None
    subtotal: float | None = None
    taxes: float | None = None
    notes: str | None = None
    supplier_id: UUID | None = None
    supplier_name: str | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)
