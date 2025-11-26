"""Module: schemas.py

Auto-generated module docstring."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Esquema para lineas
# 🧱 Línea base
class LineaBase(BaseModel):
    """Class LineaBase - auto-generated docstring."""

    description: str
    cantidad: float
    precio_unitario: float
    iva: float | None = 0


# 🥖 Línea panadería
class BakeryLine(LineaBase):
    """Class BakeryLine - auto-generated docstring."""

    sector: Literal["bakery"]
    bread_type: str
    grams: float


class BakeryLineOut(BakeryLine):
    """Class BakeryLineOut - auto-generated docstring."""

    model_config = ConfigDict(from_attributes=True)


# 🔧 Línea taller
class WorkshopLine(LineaBase):
    """Class WorkshopLine - auto-generated docstring."""

    sector: Literal["workshop"]
    spare_part: str
    labor_hours: float
    rate: float


class WorkshopLineOut(WorkshopLine):
    """Class WorkshopLineOut - auto-generated docstring."""

    model_config = ConfigDict(from_attributes=True)


# 🎯 Unión de tipos posibles
LineaFacturaIn = BakeryLine | WorkshopLine
LineaFacturaOut = Annotated[BakeryLineOut | WorkshopLineOut, Field(discriminator="sector")]

# Backward compatibility aliases
LineaPanaderia = BakeryLine
LineaPanaderiaOut = BakeryLineOut
LineaTaller = WorkshopLine
LineaTallerOut = WorkshopLineOut


# facturas
class ClienteSchema(BaseModel):
    """Class ClienteSchema - auto-generated docstring."""

    id: UUID
    name: str
    email: str
    identificacion: str
    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    """Class InvoiceCreate - auto-generated docstring."""

    numero: str
    supplier: str | None = None
    fecha_emision: str
    estado: str
    subtotal: float
    iva: float
    total: float
    cliente_id: str
    lineas: list[LineaFacturaIn]
    model_config = ConfigDict(from_attributes=True)


class InvoiceOut(BaseModel):
    """Class InvoiceOut - auto-generated docstring."""

    id: UUID
    numero: str
    fecha_emision: str
    estado: str
    subtotal: float
    iva: float
    total: float
    cliente: ClienteSchema
    lineas: list[LineaFacturaOut]  # polimórficas

    model_config = ConfigDict(from_attributes=True)


class InvoiceUpdate(BaseModel):
    """Class InvoiceUpdate - auto-generated docstring."""

    estado: str | None
    supplier: str | None
    fecha_emision: str | None
    lineas: list[LineaFacturaIn] | None


# fiiin


class FacturaTempCreate(BaseModel):
    """Class FacturaTempCreate - auto-generated docstring."""

    archivo_nombre: str
    datos: Any
    usuario_id: int


class FacturaOut(BaseModel):
    """Class FacturaOut - auto-generated docstring."""

    id: UUID
    numero: str
    supplier: str
    fecha_emision: str
    monto: int
    estado: str


class InvoiceTempOut(BaseModel):
    """Class InvoiceTempOut - auto-generated docstring."""

    pass
