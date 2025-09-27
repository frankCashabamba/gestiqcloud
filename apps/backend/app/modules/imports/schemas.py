from pydantic import BaseModel, ConfigDict
from typing import Any, Optional, List, Dict
from uuid import UUID
from datetime import datetime
from pydantic import Field

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

    model_config = ConfigDict(from_attributes=True)


class DocumentoProcesadoResponse(BaseModel):
    archivo: str
    documentos: List[DocumentoProcesado]


class OCRJobEnqueuedResponse(BaseModel):
    job_id: str
    status: str = "pending"


class OCRJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[DocumentoProcesadoResponse] = None
    error: Optional[str] = None


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class ItemOut(BaseModel):
    id: UUID
    idx: int
    status: str
    raw: Dict[str, Any] | None = None
    normalized: Dict[str, Any] | None = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    promoted_to: Optional[str] = None
    promoted_id: Optional[UUID] = None
    promoted_at: Optional[datetime] = None
    lineage: List[Dict[str, Any]] = Field(default_factory=list)
    last_correction: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ItemPatch(BaseModel):
    field: str
    value: Any


# Resultados de promoción
class PromoteResult(BaseModel):
    created: int
    skipped: int
    failed: int


# --------------------
# Ingesta de filas
# --------------------

class IngestRows(BaseModel):
    rows: List[Dict[str, Any]]
    mapping_id: Optional[UUID] = None
    transforms: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None


# --------------------
# ImportMapping (plantillas)
# --------------------

class ImportMappingBase(BaseModel):
    name: str
    source_type: str
    version: int = 1
    mappings: Optional[Dict[str, str]] = None
    transforms: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    dedupe_keys: Optional[List[str]] = None


class ImportMappingCreate(ImportMappingBase):
    pass


class ImportMappingUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[int] = None
    mappings: Optional[Dict[str, str]] = None
    transforms: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    dedupe_keys: Optional[List[str]] = None


class ImportMappingOut(ImportMappingBase):
    id: UUID
    empresa_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
