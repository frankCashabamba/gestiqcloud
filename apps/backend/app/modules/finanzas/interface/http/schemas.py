from datetime import date

from pydantic import BaseModel, ConfigDict


class MovimientoOut(BaseModel):
    id: int
    fecha: date
    concepto: str
    monto: float

    model_config = ConfigDict(from_attributes=True)
