from datetime import date

from pydantic import BaseModel, ConfigDict


class CashMovementOut(BaseModel):
    id: int
    date: date
    description: str
    amount: float

    model_config = ConfigDict(from_attributes=True)
