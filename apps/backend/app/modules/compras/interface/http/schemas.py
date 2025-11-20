from datetime import date

from pydantic import BaseModel, ConfigDict


class CompraBase(BaseModel):
    fecha: date
    total: float
    proveedor_id: int | None = None
    estado: str | None = None


class CompraCreate(CompraBase):
    pass


class CompraUpdate(CompraBase):
    pass


class CompraOut(CompraBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
