from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --------------------
# Procesamiento de documentos
# --------------------


class DocumentoProcesado(BaseModel):
    # Campos comunes detectados/normalizados por los extractores
    tipo: str | None = None  # "factura"|"recibo"|"transferencia"|"bancario"|"desconocido"
    importe: float | None = None
    cliente: str | None = None
    invoice: str | None = None
    fecha: str | None = None
    cuenta: str | None = None
    concepto: str | None = None
    categoria: str | None = None
    origen: str | None = None
    documentoTipo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentoProcesadoResponse(BaseModel):
    archivo: str
    documentos: list[DocumentoProcesado]


class OCRJobEnqueuedResponse(BaseModel):
    job_id: str
    status: str = "pending"


class OCRJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: DocumentoProcesadoResponse | None = None
    error: str | None = None


# --------------------
# Legacy schemas removed - use ImportBatch/ImportItem instead
# --------------------


class OkResponse(BaseModel):
    ok: bool = True


class HayPendientesOut(BaseModel):
    hayPendientes: bool


# --------------------
# Batches e items (para pipelines avanzados)
# --------------------


class BatchCreate(BaseModel):
    source_type: str  # 'invoices'|'bank'|'receipts'
    origin: str  # 'excel'|'ocr'|'api'
    file_key: str | None = None
    mapping_id: UUID | None = None
    # Fase A - Clasificación persistida
    suggested_parser: str | None = None
    classification_confidence: float | None = None
    ai_enhanced: bool | None = False
    ai_provider: str | None = None


class BatchOut(BaseModel):
    id: UUID
    source_type: str
    origin: str
    status: str
    file_key: str | None = None
    mapping_id: UUID | None = None
    created_at: datetime
    # Fase A - Clasificación persistida
    suggested_parser: str | None = None
    classification_confidence: float | None = None
    ai_enhanced: bool = False
    ai_provider: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UpdateClassificationRequest(BaseModel):
    """Schema para actualizar clasificación de un batch (PATCH /batches/{id}/classification)"""

    suggested_parser: str | None = None
    classification_confidence: float | None = None
    ai_enhanced: bool | None = None
    ai_provider: str | None = None


class ItemOut(BaseModel):
    id: UUID
    idx: int
    status: str
    raw: dict[str, Any] | None = None
    normalized: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    promoted_to: str | None = None
    promoted_id: UUID | None = None
    promoted_at: datetime | None = None
    lineage: list[dict[str, Any]] = Field(default_factory=list)
    last_correction: dict[str, Any] | None = None

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
    rows: list[dict[str, Any]]
    mapping_id: UUID | None = None
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None


class PromoteItems(BaseModel):
    item_ids: list[str]


# --------------------
# ImportMapping (plantillas)
# --------------------


class ImportMappingBase(BaseModel):
    name: str
    source_type: str
    version: int = 1
    mappings: dict[str, str] | None = None
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None
    dedupe_keys: list[str] | None = None


class ImportMappingCreate(ImportMappingBase):
    pass


class ImportMappingUpdate(BaseModel):
    name: str | None = None
    version: int | None = None
    mappings: dict[str, str] | None = None
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None
    dedupe_keys: list[str] | None = None


class ImportMappingOut(ImportMappingBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
