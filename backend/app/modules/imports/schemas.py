from typing import Optional, Literal, List
from pydantic import BaseModel, ConfigDict


class DatosImportadosBase(BaseModel):
    tipo: str  # ✅ acepta cualquier string
    origen: Literal["ocr", "excel", "manual"]
    datos: dict
    estado: Optional[str] = "pendiente"
    hash: Optional[str] = None


class DatosImportadosCreate(DatosImportadosBase):
    pass


class DatosImportadosUpdate(DatosImportadosBase):
    pass


class DatosImportadosOut(DatosImportadosBase):
    id: int
    empresa_id: int

    # Pydantic v2: reemplaza orm_mode=True
    model_config = ConfigDict(from_attributes=True)


class DocumentoProcesado(BaseModel):
    fecha: str
    concepto: str
    tipo: Literal["ingreso", "gasto", "movimiento"]
    importe: float
    cuenta: str
    categoria: str
    cliente: str
    invoice: Optional[str] = None
    origen: Optional[Literal["ocr", "excel", "manual"]] = "ocr"
    documentoTipo: Literal[
        "factura", "recibo", "transferencia", "nómina", "presupuesto", "contrato", "desconocido"
    ]

    # Pydantic v2: reemplaza orm_mode=True
    model_config = ConfigDict(from_attributes=True)


class DocumentoProcesadoResponse(BaseModel):
    archivo: str
    documentos: List[DocumentoProcesado]


class OkResponse(BaseModel):
    ok: bool = True


class HayPendientesOut(BaseModel):
    hayPendientes: bool
