from datetime import date

from pydantic import BaseModel, ConfigDict


class PurchaseBase(BaseModel):
    date: date
    total: float
    supplier_id: int | None = None
    status: str | None = None


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseUpdate(PurchaseBase):
    pass


class PurchaseOut(PurchaseBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
