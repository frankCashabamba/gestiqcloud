from datetime import date
from pydantic import BaseModel, ConfigDict


class VentaBase(BaseModel):
    fecha: date
    total: float
    cliente_id: int | None = None
    estado: str | None = None


class VentaCreate(VentaBase):
    pass


class VentaUpdate(VentaBase):
    pass


class VentaOut(VentaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
