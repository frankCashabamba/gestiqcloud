"""Module: schemas.py

Auto-generated module docstring."""

from typing import Annotated, Any, Literal, Union
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
class LineaPanaderia(LineaBase):
    """Class LineaPanaderia - auto-generated docstring."""

    sector: Literal["panaderia"]
    tipo_pan: str
    gramos: float


class LineaPanaderiaOut(LineaPanaderia):
    """Class LineaPanaderiaOut - auto-generated docstring."""

    model_config = ConfigDict(from_attributes=True)


# 🔧 Línea taller
class LineaTaller(LineaBase):
    """Class LineaTaller - auto-generated docstring."""

    sector: Literal["taller"]
    repuesto: str
    horas_mano_obra: float
    tarifa: float


class LineaTallerOut(LineaTaller):
    """Class LineaTallerOut - auto-generated docstring."""

    model_config = ConfigDict(from_attributes=True)


# 🎯 Unión de tipos posibles
LineaFacturaIn = Union[LineaPanaderia, LineaTaller]
LineaFacturaOut = Annotated[LineaPanaderiaOut | LineaTallerOut, Field(discriminator="sector")]


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
    proveedor: str | None = None
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
    proveedor: str | None
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
    proveedor: str
    fecha_emision: str
    monto: int
    estado: str


class InvoiceTempOut(BaseModel):
    """Class InvoiceTempOut - auto-generated docstring."""

    pass
