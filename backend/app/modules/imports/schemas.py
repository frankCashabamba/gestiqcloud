from pydantic import BaseModel
from typing import Any, Optional, List, Dict
from uuid import UUID
from datetime import datetime

# --------------------
# Procesamiento de documentos
# --------------------

class DocumentoProcesado(BaseModel):
    # Campos comunes detectados/normalizados por los extractores
    tipo: Optional[str] = None                 # "factura"|"recibo"|"transferencia"|"bancario"|"desconocido"
    importe: Optional[float] = None
    cliente: Optional[str] = None
    invoice: Optional[str] = None
    fecha: Optional[str] = None
    cuenta: Optional[str] = None
    concepto: Optional[str] = None
    categoria: Optional[str] = None
    origen: Optional[str] = None
    documentoTipo: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentoProcesadoResponse(BaseModel):
    archivo: str
    documentos: List[DocumentoProcesado]


# --------------------
# CRUD de DatosImportados
# --------------------

class DatosImportadosBase(BaseModel):
    tipo: str
    origen: str
    datos: Dict[str, Any]
    estado: Optional[str] = "pendiente"
    hash: Optional[str] = None


class DatosImportadosCreate(DatosImportadosBase):
    pass


class DatosImportadosUpdate(BaseModel):
    tipo: Optional[str] = None
    origen: Optional[str] = None
    datos: Optional[Dict[str, Any]] = None
    estado: Optional[str] = None
    hash: Optional[str] = None


class DatosImportadosOut(DatosImportadosBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True


class OkResponse(BaseModel):
    ok: bool = True


class HayPendientesOut(BaseModel):
    hayPendientes: bool


# --------------------
# Batches e items (para pipelines avanzados)
# --------------------

class BatchCreate(BaseModel):
    source_type: str            # 'invoices'|'bank'|'receipts'
    origin: str                 # 'excel'|'ocr'|'api'
    file_key: Optional[str] = None
    mapping_id: Optional[UUID] = None


class BatchOut(BaseModel):
    id: UUID
    source_type: str
    origin: str
    status: str
    file_key: Optional[str] = None
    mapping_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ItemOut(BaseModel):
    id: UUID
    idx: int
    status: str
    raw: Dict[str, Any] | None = None
    normalized: Dict[str, Any] | None = None
    errors: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class ItemPatch(BaseModel):
    field: str
    value: Any


# Resultados de promoción
class PromoteResult(BaseModel):
    created: int
    skipped: int
    failed: int
