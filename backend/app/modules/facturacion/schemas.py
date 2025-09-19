"""Module: schemas.py

Auto-generated module docstring."""

from typing import Annotated, Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


#Esquema para lineas
# 🧱 Línea base
class LineaBase(BaseModel):
    """ Class LineaBase - auto-generated docstring. """
    descripcion: str
    cantidad: float
    precio_unitario: float
    iva: Optional[float] = 0


# 🥖 Línea panadería
class LineaPanaderia(LineaBase):
    """ Class LineaPanaderia - auto-generated docstring. """
    sector: Literal["panaderia"]
    tipo_pan: str
    gramos: float

class LineaPanaderiaOut(LineaPanaderia):
    """ Class LineaPanaderiaOut - auto-generated docstring. """
    model_config = ConfigDict(from_attributes=True)
# 🔧 Línea taller
class LineaTaller(LineaBase):
    """ Class LineaTaller - auto-generated docstring. """
    sector: Literal["taller"]
    repuesto: str
    horas_mano_obra: float
    tarifa: float

class LineaTallerOut(LineaTaller):
    """ Class LineaTallerOut - auto-generated docstring. """
    model_config = ConfigDict(from_attributes=True)
# 🎯 Unión de tipos posibles
LineaFacturaIn = Union[LineaPanaderia, LineaTaller]
LineaFacturaOut = Annotated[
    Union[LineaPanaderiaOut, LineaTallerOut],
    Field(discriminator="sector")
]

#facturas
class ClienteSchema(BaseModel):
    """ Class ClienteSchema - auto-generated docstring. """
    id: int
    nombre: str
    email: str
    identificacion: str    
    model_config = ConfigDict(from_attributes=True)
class InvoiceCreate(BaseModel):
    """ Class InvoiceCreate - auto-generated docstring. """
    numero: str
    proveedor: Optional[str] = None
    fecha_emision: str
    estado: str
    subtotal: float
    iva: float
    total: float
    cliente_id: int
    lineas: List[LineaFacturaIn]
    model_config = ConfigDict(from_attributes=True)
class InvoiceOut(BaseModel):
    """ Class InvoiceOut - auto-generated docstring. """
    id: int
    numero: str
    fecha_emision: str
    estado: str
    subtotal: float
    iva: float
    total: float
    cliente: ClienteSchema
    lineas: List[LineaFacturaOut]  # polimórficas  

    model_config = ConfigDict(from_attributes=True)
class InvoiceUpdate(BaseModel):
    """ Class InvoiceUpdate - auto-generated docstring. """
    estado: Optional[str]
    proveedor: Optional[str]
    fecha_emision: Optional[str]
    lineas: Optional[List[LineaFacturaIn]]    

#fiiin



class FacturaTempCreate(BaseModel):
    """ Class FacturaTempCreate - auto-generated docstring. """
    archivo_nombre: str
    datos: Any
    usuario_id: int

class FacturaOut(BaseModel):
    """ Class FacturaOut - auto-generated docstring. """
    id: int
    numero: str
    proveedor: str
    fecha_emision: str
    monto: int
    estado: str

class InvoiceTempOut(BaseModel):
    """ Class InvoiceTempOut - auto-generated docstring. """
    pass
