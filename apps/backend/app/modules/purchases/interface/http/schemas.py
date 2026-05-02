from datetime import date as dt_date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("supplier_id", "supplier_name", "status", "subtotal", "taxes", "notes", "delivery_date", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class PurchaseCreate(PurchaseBase):
    lines: list[PurchaseLineCreate] = Field(default_factory=list)


class PurchaseUpdate(BaseModel):
    date: dt_date | None = None
    total: float | None = None
    supplier_id: str | None = None
    status: str | None = None

    @field_validator("date", "supplier_id", "status", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


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
