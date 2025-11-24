from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SaleBase(BaseModel):
    date: date
    total: float
    customer_id: str | None = None
    status: str | None = None


class SaleCreate(SaleBase):
    pass


class SaleUpdate(SaleBase):
    pass


class SaleOut(SaleBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
