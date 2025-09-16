from datetime import date
from pydantic import BaseModel


class MovimientoOut(BaseModel):
    id: int
    fecha: date
    concepto: str
    monto: float

    class Config:
        from_attributes = True

