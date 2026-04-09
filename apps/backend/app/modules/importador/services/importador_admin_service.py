from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text as sa_text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.importador import ImpConfig
from app.models.tenant import Tenant

from .. import crud
from ..category_loader import invalidate_cache as invalidate_doc_categories_cache
from ..pre_classifier import invalidate_pre_classifier_cache
from ..runtime_config import (
    ensure_runtime_config_seeded,
    invalidate_runtime_config_cache,
    list_runtime_config_modules,
)
from ..schemas import (
    BatchSummaryOut,
    DashboardStats,
    ImportadorRoutingOverviewOut,
    RuntimeConfigCatalogOut,
    RuntimeConfigEntryOut,
    RuntimeConfigEntryUpsertIn,
    RuntimeConfigModuleOut,
)
from .document_learning_queue_service import list_reprocess_candidates
from .document_routing_config import invalidate_document_routing_cache
from .document_routing_learning_insights_service import list_routing_learning_insights

RUNTIME_MODULE_TITLES: dict[str, str] = {
    "doc_type_patterns": "Doc Type Patterns",
    "doc_categories": "Document Categories",
    "filename_normalization": "Filename Normalization",
    "tax_id_patterns": "Tax ID Patterns",
    "routing_field_aliases": "Routing Field Aliases",
    "routing_field_labels": "Routing Field Labels",
    "routing_fallback_profiles": "Routing Fallback Profiles",
    "routing_fallback_rules": "Routing Fallback Rules",
    "file_support": "File Support",
    "ocr_config": "OCR Config",
    "pre_classifier": "Pre Classifier",
    "ai_runtime": "AI Runtime",
    "processing_runtime": "Processing Runtime",
    "routing_scoring": "Routing Scoring",
    "prompt_config": "Prompt Config",
    "classification": "Classification",
    "product_sheet_detection": "Product Sheet Detection",
    "amount_label_config": "Amount Label Config",
    "learning": "Learning",
    "pdf_table_parse": "PDF Table Parse",
    "ai_params": "AI Params",
    "ai_model_routing": "AI Model Routing",
    "learning_control": "Learning Control",
    "cache_ttls": "Cache TTLS",
    "fuzzy_reuse": "Fuzzy Reuse",
    "snapshot_learning": "Snapshot Learning",
}

RUNTIME_MODULE_DESCRIPTIONS: dict[str, str] = {
    "doc_categories": "Categorias usadas para clasificar el tipo documental.",
    "routing_fallback_profiles": "Perfiles base del resolver de routing.",
    "routing_fallback_rules": "Reglas base de fallback por doc_type o categoria.",
    "prompt_config": "Prompts y reglas textuales del motor AI.",
    "learning_control": "Puertas de control para reprocess y aprendizaje.",
    "cache_ttls": "TTLs de cache en memoria del importador.",
}


def _module_title(module: str) -> str:
    return RUNTIME_MODULE_TITLES.get(module, module.replace("_", " ").replace(".", " ").title())


def _module_description(module: str) -> str | None:
    return RUNTIME_MODULE_DESCRIPTIONS.get(module)


def _value_kind(value_text: str | None, value_list: list[str]) -> str:
    if value_list:
        return "list"
    text = str(value_text or "").strip()
    if text.startswith("{") or text.startswith("["):
        return "json"
    return "text"


def _normalize_list(value_list: list | None) -> list[str]:
    if not isinstance(value_list, list):
        return []
    return [str(item).strip() for item in value_list if str(item).strip()]


def _serialize_runtime_row(row: ImpConfig) -> RuntimeConfigEntryOut:
    value_list = _normalize_list(getattr(row, "value_list", None))
    value_text = getattr(row, "value_text", None)
    return RuntimeConfigEntryOut(
        id=row.id,
        module=row.module,
        key=row.key,
        label=row.label,
        value_text=value_text,
        value_list=value_list,
        value_kind=_value_kind(value_text, value_list),
        updated_at=row.updated_at,
    )


def _runtime_modules_in_order(db: Session) -> list[str]:
    ensure_runtime_config_seeded(db)
    db_modules = [
        str(module).strip()
        for (module,) in db.execute(
            sa_text("SELECT DISTINCT module FROM imp_config ORDER BY module ASC")
        ).all()
        if str(module).strip()
    ]
    ordered = list_runtime_config_modules()
    for module in db_modules:
        if module not in ordered:
            ordered.append(module)
    return ordered


def list_importador_runtime_config(db: Session) -> RuntimeConfigCatalogOut:
    modules: list[RuntimeConfigModuleOut] = []
    for module in _runtime_modules_in_order(db):
        rows = (
            db.query(ImpConfig)
            .filter(ImpConfig.module == module)
            .order_by(ImpConfig.key.asc())
            .all()
        )
        modules.append(
            RuntimeConfigModuleOut(
                module=module,
                title=_module_title(module),
                description=_module_description(module),
                editable=True,
                entries=[_serialize_runtime_row(row) for row in rows],
            )
        )
    return RuntimeConfigCatalogOut(modules=modules)


def _invalidate_runtime_caches(module: str) -> None:
    normalized = str(module or "").strip()
    invalidate_runtime_config_cache()
    if normalized == "doc_categories":
        invalidate_doc_categories_cache()
    if normalized == "pre_classifier":
        invalidate_pre_classifier_cache()
    if normalized in {"routing_fallback_profiles", "routing_fallback_rules"}:
        invalidate_document_routing_cache()


def upsert_runtime_config_entry(
    db: Session,
    *,
    module: str,
    key: str,
    payload: RuntimeConfigEntryUpsertIn,
) -> RuntimeConfigEntryOut:
    normalized_module = str(module or "").strip().lower()
    normalized_key = str(key or "").strip()
    if not normalized_module:
        raise HTTPException(status_code=400, detail="runtime_module_required")
    if not normalized_key:
        raise HTTPException(status_code=400, detail="runtime_key_required")

    row = (
        db.query(ImpConfig)
        .filter(ImpConfig.module == normalized_module, ImpConfig.key == normalized_key)
        .first()
    )
    if row is None:
        row = ImpConfig(module=normalized_module, key=normalized_key)
        db.add(row)

    row.label = payload.label
    row.value_text = str(payload.value_text).strip() if payload.value_text is not None else None
    row.value_list = _normalize_list(payload.value_list)
    db.commit()
    db.refresh(row)
    _invalidate_runtime_caches(normalized_module)
    return _serialize_runtime_row(row)


def delete_runtime_config_entry(db: Session, *, module: str, key: str) -> dict[str, bool]:
    normalized_module = str(module or "").strip().lower()
    normalized_key = str(key or "").strip()
    row = (
        db.query(ImpConfig)
        .filter(ImpConfig.module == normalized_module, ImpConfig.key == normalized_key)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="runtime_config_entry_not_found")
    db.delete(row)
    db.commit()
    _invalidate_runtime_caches(normalized_module)
    return {"ok": True}


def reset_runtime_config_module(db: Session, *, module: str) -> dict[str, bool]:
    normalized_module = str(module or "").strip().lower()
    if not normalized_module:
        raise HTTPException(status_code=400, detail="runtime_module_required")
    db.query(ImpConfig).filter(ImpConfig.module == normalized_module).delete()
    db.commit()
    _invalidate_runtime_caches(normalized_module)
    return {"ok": True}


def build_importador_routing_overview(
    db: Session,
    *,
    tenant_id: UUID,
    limit: int = 8,
) -> ImportadorRoutingOverviewOut:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")

    counts = crud.count_documentos(db, tenant_id)
    dashboard = DashboardStats(
        total=sum(int(value) for value in counts.values()),
        pendientes=int(counts.get("PENDING", 0)) + int(counts.get("PROCESSING", 0)),
        en_revision=int(counts.get("REVIEW", 0)),
        confirmados=int(counts.get("CONFIRMED", 0)),
        fallidos=int(counts.get("FAILED", 0)),
    )

    recent_batches = [
        BatchSummaryOut(**crud.summarize_batch(db, batch))
        for batch in crud.list_batches(
            db,
            tenant_id,
            active_only=False,
            limit=max(1, min(limit, 20)),
        )
    ]
    recent_documents = crud.list_documentos(
        db,
        tenant_id,
        limit=max(1, min(limit, 20)),
    )
    try:
        reprocess_queue = list_reprocess_candidates(
            db, tenant_id=tenant_id, limit=max(1, min(limit, 20))
        )
    except SQLAlchemyError:
        reprocess_queue = []
    try:
        learning_insights = list_routing_learning_insights(
            db, tenant_id=tenant_id, limit=max(1, min(limit, 10))
        )
    except SQLAlchemyError:
        learning_insights = []

    return ImportadorRoutingOverviewOut(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        dashboard=dashboard,
        recent_batches=recent_batches,
        recent_documents=recent_documents,
        reprocess_queue=reprocess_queue,
        learning_insights=learning_insights,
    )
