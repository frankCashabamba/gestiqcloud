"""Pydantic schemas for Importador module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentRoutingDecision(BaseModel):
    document_type: str
    confidence: float = Field(ge=0, le=1)
    required_fields_ok: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    suggested_destination: Literal["recipe", "expense", "supplier_invoice"] | None = None
    reason: str = ""
    needs_human_review: bool = False
    source_doc_type: str | None = None
    source_category: str | None = None


class DocumentReviewHintOut(BaseModel):
    field: str
    field_type: str = "text"
    priority: int = Field(default=1, ge=1)
    is_missing: bool = False
    corrected_count: int = 0
    confirmed_count: int = 0
    confirmed_examples: list[str] = Field(default_factory=list)
    last_confirmed_value: str | None = None
    reason: str = ""


class AssistedReviewOut(BaseModel):
    mode: Literal["assisted_lines"]
    reason: str
    message: str = ""
    line_items_count: int = Field(default=0, ge=0)
    scalar_fields_detected: int = Field(default=0, ge=0)
    can_derive_total: bool = False


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
    routing_decision: DocumentRoutingDecision | None = None
    review_hints: list[DocumentReviewHintOut] = Field(default_factory=list)
    assisted_review: AssistedReviewOut | None = None
    last_processing_reason: str | None = None
    last_learning_reprocess_at: datetime | None = None
    last_confirmation_mode: str | None = None
    synced_sheets: dict | None = None
    saved_as: str | None = None
    saved_record_id: UUID | None = None
    saved_at: datetime | None = None
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
    assisted_review: AssistedReviewOut | None = None
    last_processing_reason: str | None = None
    last_learning_reprocess_at: datetime | None = None
    last_confirmation_mode: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogCambioOut(BaseModel):
    id: UUID
    accion: str
    detalle: dict | None = None
    usuario_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentoVersionLinkOut(BaseModel):
    id: UUID
    nombre_archivo: str
    estado: str
    hash_sha256: str | None = None
    tipo_documento_detectado: str | None = None
    created_at: datetime
    updated_at: datetime
    relation_direction: Literal["predecessor", "successor"]
    relation_reason: str | None = None
    depth: int = 1


class DocumentoDetailOut(DocumentoOut):
    logs: list[LogCambioOut] = []
    version_links: list[DocumentoVersionLinkOut] = Field(default_factory=list)


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


class BatchItemOut(BaseModel):
    id: UUID
    batch_id: UUID
    documento_id: UUID | None = None
    nombre_archivo: str
    tamanio_bytes: int
    estado: str
    error_detalle: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BatchSummaryOut(BaseModel):
    id: UUID
    estado: str
    total_items: int = 0
    pending_items: int = 0
    processing_items: int = 0
    review_items: int = 0
    confirmed_items: int = 0
    failed_items: int = 0
    progress_pct: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class BatchDetailOut(BatchSummaryOut):
    items: list[BatchItemOut] = Field(default_factory=list)


class UploadResponse(BaseModel):
    id: UUID
    estado: str
    tipo_documento_detectado: str | None = None
    confianza_clasificacion: float | None = None
    requiere_revision: bool = False
    datos_extraidos: dict | None = None
    routing_decision: DocumentRoutingDecision | None = None
    review_hints: list[DocumentReviewHintOut] = Field(default_factory=list)
    assisted_review: AssistedReviewOut | None = None
    action: Literal["CREATED", "REUSED", "REPROCESS"] = "CREATED"
    message: str | None = None


class SaveDocumentLineMatch(BaseModel):
    line_index: int = Field(ge=0)
    product_id: UUID | None = None
    persist_alias: bool = True
    create_new: bool = False


class SaveDocumentRequest(BaseModel):
    destination: Literal["recipe", "expense", "supplier_invoice"] | None = None
    payment_status: Literal["pending", "partial", "paid"] = "pending"
    paid_amount: float | None = Field(default=None, ge=0)
    pending_amount: float | None = Field(default=None, ge=0)
    payment_method: str | None = Field(default=None, max_length=64)
    payment_method_id: UUID | str | None = None
    paid_at: str | None = None
    notes: str | None = None
    update_stock: bool = False
    warehouse_id: UUID | None = None
    line_matches: list[SaveDocumentLineMatch] = Field(default_factory=list)


class SaveDocumentResponse(BaseModel):
    target: Literal["recipes", "expenses", "purchases"]
    destination: Literal["recipe", "expense", "supplier_invoice"]
    status: Literal["created", "updated", "skipped", "stock_updated"]
    record_id: str | None = None
    record_ids: list[str] = Field(default_factory=list)
    message: str | None = None


class ProductMatchCandidateOut(BaseModel):
    product_id: UUID
    name: str
    sku: str | None = None
    unit: str
    stock: float = 0
    score: float = Field(default=0, ge=0, le=1)
    reason: str
    inferred_factor: float = Field(default=1, gt=0)


class DocumentLineMatchOut(BaseModel):
    line_index: int = Field(ge=0)
    description: str
    quantity: float = 0
    unit_price: float = 0
    selected_product_id: UUID | None = None
    selected_reason: str | None = None
    inferred_factor: float = Field(default=1, gt=0)
    candidates: list[ProductMatchCandidateOut] = Field(default_factory=list)


class DocumentLineMatchesResponse(BaseModel):
    lines: list[DocumentLineMatchOut] = Field(default_factory=list)


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


# -----------  v1.3 Recipe / Run schemas  -----------


class RunResponse(BaseModel):
    id: UUID
    estado: str
    tipo_documento_detectado: str | None = None
    confianza_clasificacion: float | None = None
    requiere_revision: bool = False
    datos_extraidos: dict | None = None
    routing_decision: DocumentRoutingDecision | None = None
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


# ─────── Iterative Reprocessing Schemas ───────────────────────────────────


class StagingLineSummary(BaseModel):
    pending: int = 0
    valid: int = 0
    imported: int = 0
    invalid: int = 0
    review: int = 0
    skipped: int = 0
    reprocess: int = 0

    @property
    def total(self) -> int:
        return sum(
            [
                self.pending,
                self.valid,
                self.imported,
                self.invalid,
                self.review,
                self.skipped,
                self.reprocess,
            ]
        )

    @property
    def resolvable(self) -> int:
        return self.pending + self.invalid + self.review + self.reprocess


class StagingLineOut(BaseModel):
    id: UUID
    line_number: int
    sheet_name: str | None = None
    raw_data: dict
    normalized_data: dict | None = None
    estado: str
    error_code: str | None = None
    error_detail: str | None = None
    campos_revision: list[str] | None = None
    target_table: str | None = None
    target_id: UUID | None = None
    imported_at: datetime | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class IterationScopeIn(BaseModel):
    mode: Literal["ALL", "SELECTIVE"] = "ALL"
    filter_estados: list[str] = Field(default_factory=list)
    filter_error_codes: list[str] = Field(default_factory=list)
    filter_campos: list[str] = Field(default_factory=list)
    filter_columns: list[str] = Field(default_factory=list)
    filter_lines: list[int] = Field(default_factory=list)
    filter_sheet: str | None = None


class IterationOut(BaseModel):
    id: UUID
    iteration_num: int
    scope: str
    scope_filter: dict | None = None
    lines_attempted: int = 0
    lines_imported: int = 0
    lines_errored: int = 0
    lines_skipped: int = 0
    improvement: bool | None = None
    estado: str
    started_at: datetime
    completed_at: datetime | None = None
    initiated_by: str | None = None

    model_config = {"from_attributes": True}


class IterationResultOut(BaseModel):
    iteration_id: UUID
    iteration_num: int
    estado: str
    improvement: bool
    lines_attempted: int
    lines_imported: int
    lines_errored: int
    lines_skipped: int
    remaining: StagingLineSummary
    can_retry: bool
    message: str | None = None


class ReuploadResponse(BaseModel):
    documento_id: UUID
    action: Literal["FULLY_IMPORTED", "READY_TO_ITERATE", "NEW_FILE"]
    message: str
    stats: StagingLineSummary
    can_reprocess: bool
    suggested_scope: IterationScopeIn | None = None


class RunIterationRequest(BaseModel):
    scope: IterationScopeIn = Field(default_factory=IterationScopeIn)


class ReviewSessionCreate(BaseModel):
    filter_estados: list[str] = Field(default_factory=list)
    filter_error_codes: list[str] = Field(default_factory=list)
    filter_campos: list[str] = Field(default_factory=list)
    filter_columns: list[str] = Field(default_factory=list)
    filter_lines: list[int] = Field(default_factory=list)
    filter_sheet: str | None = None


class ReviewSessionOut(BaseModel):
    id: UUID
    documento_id: UUID
    filter_estados: list[str]
    filter_error_codes: list[str]
    filter_campos: list[str]
    filter_columns: list[str]
    filter_lines: list[int]
    filter_sheet: str | None = None
    preview_count: int
    estado: str
    created_at: datetime
    linked_iteration_id: UUID | None = None

    model_config = {"from_attributes": True}


class BulkStagingPatch(BaseModel):
    line_ids: list[UUID] = Field(min_length=1)
    estado: Literal["REPROCESS", "REVIEW", "SKIPPED"]
    campos_revision: list[str] | None = None


class StagingLinePatch(BaseModel):
    estado: Literal["REPROCESS", "REVIEW", "SKIPPED"] | None = None
    campos_revision: list[str] | None = None
    normalized_data: dict | None = None


class FieldStatOut(BaseModel):
    field: str
    total_lines: int
    filled: int
    empty: int
    with_error: int
    sample_values: list[str]
    related_error_codes: list[str]
    suggested_for_reprocess: bool
    fill_rate: float


class FieldAnalysisResponse(BaseModel):
    total_lines_analyzed: int
    fields: list[FieldStatOut]
    suggested_reprocess_fields: list[str]
    error_summary: dict[str, int]


class RoutingProfileAdminIn(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    document_type: str = Field(min_length=2, max_length=80)
    description: str | None = None
    suggested_destination: Literal["recipe", "expense", "supplier_invoice"] | None = None
    required_groups: list[list[str]] = Field(default_factory=list)
    support_fields: list[str] = Field(default_factory=list)
    explanation_fields: list[str] = Field(default_factory=list)
    blocked: bool = False
    confidence_threshold: float = Field(default=0.8, ge=0, le=1)
    active: bool = True


class RoutingProfileAdminOut(BaseModel):
    id: UUID
    code: str
    document_type: str
    description: str | None = None
    suggested_destination: Literal["recipe", "expense", "supplier_invoice"] | None = None
    required_groups: list[list[str]] = Field(default_factory=list)
    support_fields: list[str] = Field(default_factory=list)
    explanation_fields: list[str] = Field(default_factory=list)
    blocked: bool = False
    confidence_threshold: float = Field(ge=0, le=1)
    active: bool = True

    model_config = {"from_attributes": True}


class RoutingRuleAdminIn(BaseModel):
    scope_kind: Literal["system", "sector", "tenant"]
    tenant_id: UUID | None = None
    sector: str | None = Field(default=None, max_length=100)
    source_kind: Literal["doc_type", "category"]
    source_key: str = Field(min_length=1, max_length=80)
    profile_code: str = Field(min_length=2, max_length=80)
    priority: int = Field(default=100, ge=0, le=10000)
    active: bool = True


class RoutingRuleAdminOut(BaseModel):
    id: UUID
    scope_kind: Literal["system", "sector", "tenant"]
    tenant_id: UUID | None = None
    sector: str | None = None
    source_kind: Literal["doc_type", "category"]
    source_key: str
    profile_code: str
    priority: int
    active: bool = True

    model_config = {"from_attributes": True}


class RoutingPreviewRequest(BaseModel):
    scope_kind: Literal["system", "sector", "tenant"] = "system"
    document_id: UUID | None = None
    tenant_id: UUID | None = None
    sector: str | None = Field(default=None, max_length=100)
    source_doc_type: str | None = Field(default=None, max_length=120)
    source_category: str | None = Field(default=None, max_length=120)
    ai_confidence: float = Field(default=0.85, ge=0, le=1)
    extracted_data: dict = Field(default_factory=dict)
    canonical_fields: dict = Field(default_factory=dict)
    requires_review: bool = False
    destination_override: Literal["recipe", "expense", "supplier_invoice"] | None = None


class RoutingPreviewResponse(BaseModel):
    decision: DocumentRoutingDecision
    profile_code: str
    matched_by: str
    matched_scope: Literal["destination_override", "tenant", "sector", "system", "fallback"]
    rule_source_kind: Literal["doc_type", "category"] | None = None
    rule_source_key: str | None = None
    resolved_sector: str
    document_id: UUID | None = None
    document_name: str | None = None
    tenant_id: UUID | None = None


class RoutingPreviewDocumentOut(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre_archivo: str
    tipo_documento_detectado: str | None = None
    estado: str
    created_at: datetime
    proveedor_detectado: str | None = None
    monto_total: float | None = None

    model_config = {"from_attributes": True}


class RoutingLearningInsightOut(BaseModel):
    source_doc_type: str
    document_type: str
    signals_count: int = 0
    save_count: int = 0
    confirm_count: int = 0
    edit_count: int = 0
    top_missing_fields: list[str] = Field(default_factory=list)
    top_changed_fields: list[str] = Field(default_factory=list)
    suggested_required_groups: list[list[str]] = Field(default_factory=list)
    suggested_support_fields: list[str] = Field(default_factory=list)
    suggested_confidence_threshold: float = Field(default=0.8, ge=0, le=1)
    avg_success_confidence: float = Field(default=0.0, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class RoutingProfileUpdateProposalOut(BaseModel):
    profile_code: str
    current_profile: RoutingProfileAdminOut
    proposed_update: RoutingProfileAdminIn
    based_on: RoutingLearningInsightOut
