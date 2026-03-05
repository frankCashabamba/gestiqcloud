"""Pydantic schemas for Importador module."""
from __future__ import annotations
from datetime import datetime
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
    llm_model: str | None = None
    raw_ai_json: dict | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


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
