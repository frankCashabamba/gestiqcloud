"""Pydantic schemas for Importador module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentoOut(BaseModel):
    id: UUID
    nombre_archivo: str
    tipo_archivo: str
    tamanio_bytes: int
    tipo_documento_detectado: str | None = None
    confianza_clasificacion: float | None = None
    requiere_revision: bool = False
    datos_extraidos: dict | None = None
    datos_confirmados: dict | None = None
    estado: str
    error_detalle: str | None = None
    proveedor_detectado: str | None = None
    ruc_detectado: str | None = None
    monto_total: float | None = None
    moneda: str | None = None
    fecha_documento: str | None = None
    usuario_id: str | None = None
    created_at: datetime
    recipe_snapshot_id: UUID | None = None
    synced_recipe_id: UUID | None = None
    llm_model: str | None = None
    raw_ai_json: dict | None = None
    synced_sheets: dict | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncRecipeResponse(BaseModel):
    recipe_id: UUID
    recipe_name: str
    was_new: bool
    total_cost: float
    ingredients_count: int


class SyncRecipeSheetResponse(BaseModel):
    sheet_name: str
    status: str
    recipe_id: UUID | None = None
    recipe_name: str | None = None
    was_new: bool = False
    total_cost: float = 0
    ingredients_count: int = 0
    message: str | None = None


class SyncRecipesResponse(BaseModel):
    total_sheets: int
    processed_count: int
    skipped_count: int
    results: list[SyncRecipeSheetResponse]


class DocumentoListOut(BaseModel):
    id: UUID
    nombre_archivo: str
    tipo_archivo: str
    tipo_documento_detectado: str | None = None
    confianza_clasificacion: float | None = None
    requiere_revision: bool = False
    estado: str
    proveedor_detectado: str | None = None
    monto_total: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogCambioOut(BaseModel):
    id: UUID
    accion: str
    detalle: dict | None = None
    usuario_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentoDetailOut(DocumentoOut):
    logs: list[LogCambioOut] = []


class ConfirmRequest(BaseModel):
    datos_confirmados: dict


class EditFieldsRequest(BaseModel):
    campos: dict


class DashboardStats(BaseModel):
    total: int = 0
    pendientes: int = 0
    en_revision: int = 0
    confirmados: int = 0
    fallidos: int = 0


class UploadResponse(BaseModel):
    id: UUID
    estado: str
    tipo_documento_detectado: str | None = None
    confianza_clasificacion: float | None = None
    requiere_revision: bool = False
    datos_extraidos: dict | None = None


class SaveDocumentRequest(BaseModel):
    destination: Literal["recipe", "expense", "supplier_invoice"] | None = None
    payment_status: Literal["pending", "partial", "paid"] = "pending"
    paid_amount: float | None = Field(default=None, ge=0)
    pending_amount: float | None = Field(default=None, ge=0)
    payment_method: str | None = Field(default=None, max_length=32)
    paid_at: str | None = None
    notes: str | None = None
    update_stock: bool = False
    warehouse_id: UUID | None = None


class SaveDocumentResponse(BaseModel):
    target: Literal["recipes", "expenses", "purchases"]
    destination: Literal["recipe", "expense", "supplier_invoice"]
    status: Literal["created", "updated", "skipped", "stock_updated"]
    record_id: str | None = None
    record_ids: list[str] = Field(default_factory=list)
    message: str | None = None


class SaveDailyLogRequest(BaseModel):
    """Permite sobreescribir la fecha si el usuario la corrige."""

    log_date: str | None = None  # ISO 8601 YYYY-MM-DD; si None se infiere del nombre de archivo


class SaveDailyLogResponse(BaseModel):
    log_date: str
    inserted: int
    matched_recipes: int
    unmatched_products: list[str] = Field(default_factory=list)


class SaveProductsFromDocumentRequest(BaseModel):
    sheet_name: str | None = None
    row_indexes: list[int] = Field(default_factory=list)
    category_name: str | None = Field(default=None, max_length=200)


class SaveProductsFromDocumentResponse(BaseModel):
    sheet_name: str | None = None
    category_name: str | None = None
    created: int = 0
    updated: int = 0
    skipped_existing: int = 0
    skipped_invalid: int = 0
    product_ids: list[str] = Field(default_factory=list)
    skipped_names: list[str] = Field(default_factory=list)


class SaveAsPurchaseRequest(BaseModel):
    warehouse_id: UUID | None = None  # None → primer almacén activo del tenant
    notes: str | None = None


class SaveAsPurchaseResponse(BaseModel):
    purchase_id: UUID
    status: Literal["created", "skipped", "stock_updated"]
    lines_created: int = 0
    lines_matched: int = 0
    unmatched_descriptions: list[str] = Field(default_factory=list)
    message: str | None = None


# -----------  v1.3 Recipe / Run schemas  -----------


class RunRequest(BaseModel):
    recipe_id: UUID | None = None
    recipe_snapshot_id: UUID | None = None
    recipe_draft: dict | None = None


class RunResponse(BaseModel):
    id: UUID
    estado: str
    tipo_documento_detectado: str | None = None
    confianza_clasificacion: float | None = None
    requiere_revision: bool = False
    datos_extraidos: dict | None = None
    llm_model: str | None = None
    recipe_used: str | None = None
    recipe_snapshot_id: UUID | None = None
    auto_recipe_created: bool | None = None
    auto_recipe_name: str | None = None


class RecipeCreate(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = False


class RecipeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    archived: bool | None = None


class RecipeOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_public: bool = False
    archived: bool = False
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DraftCreate(BaseModel):
    prompt_system: str | None = None
    prompt_user: str | None = None
    ai_model_config: dict | None = None


class DraftUpdate(BaseModel):
    prompt_system: str | None = None
    prompt_user: str | None = None
    ai_model_config: dict | None = None


class DraftOut(BaseModel):
    id: UUID
    recipe_id: UUID
    prompt_system: str | None = None
    prompt_user: str | None = None
    ai_model_config: dict | None = Field(default=None, validation_alias="model_config")
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SnapshotOut(BaseModel):
    id: UUID
    recipe_id: UUID
    draft_id: UUID | None = None
    version_tag: str | None = None
    content_json: dict
    created_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
