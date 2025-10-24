from datetime import date
from pydantic import BaseModel, ConfigDict


class GastoBase(BaseModel):
    fecha: date
    monto: float
    proveedor_id: int | None = None
    concepto: str | None = None


class GastoCreate(GastoBase):
    pass


class GastoUpdate(GastoBase):
    pass


class GastoOut(GastoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
