from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from . import crud, recipe_crud
from .analysis_normalizer import _normalize_analysis_output
from .auto_recipe import (
    _snapshot_recipe_config,
    get_snapshot_learning,
    get_snapshot_learning_version,
    remember_snapshot_learning,
    resolve_auto_recipe,
    resolve_auto_recipe_from_text,
)
from .canonical_document import build_document_projection
from .category_loader import get_doc_categories
from .classifier_learning import learn_column_candidates as _learn_column_candidates
from .field_alias_loader import get_canonical_fields, get_field_aliases
from .pre_classifier import PreClassResult, classify_before_ai, load_pre_classifier_config
from .product_import_service import looks_like_product_document
from .runtime_config import (
    load_ai_runtime_config,
    load_amount_label_config,
    load_classification_threshold,
    load_doc_type_patterns,
    load_learning_control,
    load_ocr_runtime_config,
    load_pdf_table_parse_config,
    load_processing_runtime_config,
    load_product_sheet_detection_config,
    load_prompt_config,
)
from .schemas import DocumentReviewHintOut, DocumentRoutingDecision
from .services.document_model_learning_service import (
    build_signal_learning_recipe_config,
    should_run_learning_rerun,
    summarize_learning_rerun,
)
from .services.document_routing_agent import build_document_routing_decision
from .services.iteration_service import upsert_staging_lines_from_extraction
from .snapshot_learning import build_snapshot_review_hints
from .text_fallback_extractor import (
    extract_fields_from_text,
    extract_line_items_table_preview_from_text,
    learn_labels_from_text,
)
from .ai_classifier import _apply_high_evidence_ocr_repairs, _estimate_text_quality
from .utils import json_safe as _json_safe

logger = logging.getLogger("importador.processing")

AnalyzeDocumentFn = Callable[..., Awaitable[dict[str, Any]]]
ExtractTextFn = Callable[..., Awaitable[dict[str, Any]]]
ProcessingMode = Literal["run", "async"]


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))


def _set_stage_timing(stage_timings: dict[str, int], stage_name: str, started_at: float) -> int:
    elapsed = _elapsed_ms(started_at)
    stage_timings[stage_name] = elapsed
    return elapsed


def _build_timing_summary(*, stage_timings: dict[str, int], started_at: float) -> dict[str, Any]:
    ordered = {key: stage_timings[key] for key in sorted(stage_timings)}
    return {
        "timings_ms": ordered,
        "total_processing_ms": _elapsed_ms(started_at),
    }


def _build_table_prompt_preview(
    table_preview: dict[str, Any],
    *,
    max_rows: int,
) -> str:
    headers = [
        str(header).strip()
        for header in (table_preview.get("headers") or [])
        if str(header).strip()
    ]
    headers_norm = [str(header).strip() for header in (table_preview.get("headers_norm") or [])]
    line_items = table_preview.get("line_items")
    line_item_page_groups = table_preview.get("line_item_page_groups")
    if not headers or not isinstance(line_items, list) or not line_items:
        return ""

    rows: list[str] = ["Tabla detectada con headers preservados del OCR:"]
    if isinstance(line_item_page_groups, list) and line_item_page_groups:
        total_rows = 0
        for group in line_item_page_groups:
            if not isinstance(group, dict):
                continue
            group_headers = [
                str(header).strip()
                for header in (group.get("headers") or [])
                if str(header).strip()
            ]
            group_headers_norm = [
                str(header).strip() for header in (group.get("headers_norm") or [])
            ]
            page_label = str(group.get("source_page") or "").strip()
            rows.append(f"Pagina {page_label or '?'}:")
            if group_headers:
                rows.append("Headers: " + " | ".join(group_headers))
            group_items = group.get("line_items")
            if not isinstance(group_items, list):
                continue
            for item in group_items:
                if not isinstance(item, dict):
                    continue
                values: list[str] = []
                extra_columns = (
                    item.get("extra_columns") if isinstance(item.get("extra_columns"), dict) else {}
                )
                for raw_header, canonical_header in zip(group_headers, group_headers_norm):
                    value = item.get(canonical_header)
                    if value is None and isinstance(extra_columns, dict):
                        value = extra_columns.get(raw_header)
                    if value is None and raw_header in item:
                        value = item.get(raw_header)
                    values.append(str(value or ""))
                rows.append(" | ".join(values))
                total_rows += 1
                if total_rows >= max_rows:
                    return "\n".join(rows)
        return "\n".join(rows)

    rows.append("Headers: " + " | ".join(headers))

    preview_rows = 0
    for item in line_items:
        if not isinstance(item, dict):
            continue
        values: list[str] = []
        extra_columns = (
            item.get("extra_columns") if isinstance(item.get("extra_columns"), dict) else {}
        )
        for raw_header, canonical_header in zip(headers, headers_norm):
            value = item.get(canonical_header)
            if value is None and isinstance(extra_columns, dict):
                value = extra_columns.get(raw_header)
            if value is None and raw_header in item:
                value = item.get(raw_header)
            values.append(str(value or ""))
        rows.append(" | ".join(values))
        preview_rows += 1
        if preview_rows >= max_rows:
            break

    return "\n".join(rows)


def _runtime_doc_type_set(processing_cfg: dict[str, Any], key: str) -> set[str]:
    return {
        str(item).strip().upper() for item in (processing_cfg.get(key) or []) if str(item).strip()
    }


def _runtime_text_list(processing_cfg: dict[str, Any], key: str) -> list[str]:
    return [str(item).strip() for item in (processing_cfg.get(key) or []) if str(item).strip()]


def _analysis_indicates_ai_failure(
    analysis: dict[str, Any],
    *,
    processing_cfg: dict[str, Any] | None = None,
) -> bool:
    """Detect whether the AI analysis failed (timeout, connection error, etc.)."""
    if bool(analysis.get("fast_mode_skip_ai_due_to_sufficient_text")):
        return True
    combined = " ".join(
        str(analysis.get(k, "") or "") for k in ("raw_response", "reasoning", "error", "model_used")
    ).lower()
    if "fast_mode_text_sufficient_skip" in combined:
        return True
    if "no_allowed_extraction_model" in combined:
        return True
    cfg = processing_cfg or load_processing_runtime_config(None)
    return any(token.lower() in combined for token in _runtime_text_list(cfg, "ai_failure_tokens"))


def _project_line_item_slots(
    datos_extraidos: dict[str, Any],
    canonical_fields: dict[str, dict],
) -> None:
    """Proyecta claves canónicas de line_items a sus slot estándar, in-place.

    Cuando un campo canónico tiene line_item_slot definido y la clave canónica
    existe en el item, la renombra al slot. Así el frontend puede leer siempre
    el mismo nombre (el slot) independientemente del alias original del documento.
    """
    items = datos_extraidos.get("line_items")
    if not isinstance(items, list):
        return

    # canonical_name → slot_name (solo los que tienen slot)
    slot_map = {
        name: cfg["line_item_slot"]
        for name, cfg in canonical_fields.items()
        if cfg.get("line_item_slot")
    }

    for item in items:
        if not isinstance(item, dict):
            continue
        for canonical, slot in slot_map.items():
            if canonical == slot:
                continue
            if canonical in item:
                if slot not in item:
                    item[slot] = item.pop(canonical)
                else:
                    item.pop(canonical)


def _normalize_line_item_extra_columns(
    datos_extraidos: dict[str, Any],
    field_aliases: dict[str, list[str]],
) -> list[str]:
    """Normaliza extra_columns en line_items usando el mapa de aliases de la BD.

    Para cada item de line_items, toma las claves de extra_columns, las busca en
    el mapa inverso de aliases (e.g. "ref." -> "supplier_ref") y las promueve
    al nivel del item con el nombre canónico. Modifica datos_extraidos in-place.
    Usa _normalize_alias de classifier_learning para consistencia con el sistema de aprendizaje.

    Retorna la lista de nombres de columnas que NO pudieron mapearse, para
    ser registrados en imp_column_candidate por el caller.
    """
    from .classifier_learning import _normalize_alias

    items = datos_extraidos.get("line_items")
    if not isinstance(items, list):
        return []

    reverse_map: dict[str, str] = {}
    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            reverse_map[_normalize_alias(alias)] = canonical

    unmapped: list[str] = []
    seen_unmapped: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        extra = item.pop("extra_columns", None)
        if not isinstance(extra, dict):
            continue
        remaining_extra: dict[str, Any] = {}
        for col_name, col_value in extra.items():
            canonical = reverse_map.get(_normalize_alias(col_name))
            if canonical and canonical not in item:
                item[canonical] = col_value
            elif not canonical and col_name not in seen_unmapped:
                unmapped.append(col_name)
                seen_unmapped.add(col_name)
                remaining_extra[col_name] = col_value
            elif not canonical:
                remaining_extra[col_name] = col_value
        if remaining_extra:
            item["extra_columns"] = remaining_extra

    return unmapped


def _merge_text_fallback_fields(
    datos_extraidos: dict[str, Any],
    fallback_fields: dict[str, Any],
) -> bool:
    """Merge OCR text-fallback fields into an existing extraction result."""
    changed = False
    for key, value in fallback_fields.items():
        if key == "line_items":
            if value and not datos_extraidos.get(key):
                datos_extraidos[key] = value
                changed = True
            continue

        if datos_extraidos.get(key) in (None, "", [], {}):
            datos_extraidos[key] = value
            changed = True

    return changed


def _sanitize_text_fallback_fields(
    fallback_fields: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    prompt_config: dict[str, Any] | None,
    ai_runtime: dict[str, Any] | None,
    ocr_runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    """Drop noisy OCR fallback values and apply high-evidence repairs."""
    cleaned = dict(fallback_fields or {})
    if not cleaned:
        return {}

    # Reuse existing high-evidence repair rules from AI path without calling heavy LLM.
    try:
        parsed = {"doc_type": "OTHER", "fields": cleaned}
        _apply_high_evidence_ocr_repairs(
            parsed,
            content=content,
            format_hint=format_hint,
            prompt_config=prompt_config,
            ai_runtime=ai_runtime,
            ocr_runtime=ocr_runtime,
        )
        fields_after_repairs = parsed.get("fields")
        if isinstance(fields_after_repairs, dict):
            cleaned = dict(fields_after_repairs)
    except Exception as exc:
        logger.debug("text fallback OCR repair skipped due to error: %s", exc)

    removed: list[str] = []

    for key in ("vendor_tax_id", "customer_tax_id"):
        value = cleaned.get(key)
        if value in (None, ""):
            continue
        digits = re.sub(r"[^0-9]", "", str(value))
        if 10 <= len(digits) <= 15:
            cleaned[key] = digits
        else:
            cleaned.pop(key, None)
            removed.append(key)

    for key in ("vendor", "customer"):
        value = cleaned.get(key)
        raw = " ".join(str(value or "").split()).strip()
        if not raw:
            continue
        alpha = sum(1 for ch in raw if ch.isalpha())
        weird = sum(1 for ch in raw if not (ch.isalnum() or ch.isspace() or ch in ".,&-/()"))
        alpha_ratio = alpha / max(len(raw), 1)
        weird_ratio = weird / max(len(raw), 1)
        if alpha < 4 or alpha_ratio < 0.3 or weird_ratio > 0.12:
            cleaned.pop(key, None)
            removed.append(key)
            continue
        cleaned[key] = raw[:140]

    issue_date = cleaned.get("issue_date")
    if issue_date not in (None, ""):
        normalized_date = str(issue_date).strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", normalized_date):
            cleaned.pop("issue_date", None)
            removed.append("issue_date")

    if removed:
        logger.info("text_fallback_sanitized removed_fields=%s", sorted(set(removed)))

    return cleaned


@dataclass(slots=True)
class RecipeContext:
    recipe_config: dict[str, Any] = field(default_factory=dict)
    resolution_mode: str = "zero_shot"
    resolved_snapshot_id: UUID | str | None = None
    explicit_recipe_context: bool = False
    force_clean_reimport: bool = False
    recipe_id: UUID | None = None
    reprocess_mode: str = "fast"
    reprocess_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentProcessingResult:
    tipo_documento_detectado: str
    confianza_clasificacion: float
    requiere_revision: bool
    datos_extraidos: dict[str, Any] | None
    llm_model: str
    recipe_snapshot_id: UUID | str | None = None
    recipe_used: str | None = None
    routing_decision: DocumentRoutingDecision | None = None
    review_hints: list[DocumentReviewHintOut] = field(default_factory=list)
    auto_recipe_created: bool | None = None
    auto_recipe_name: str | None = None
    raw_ai_json: dict[str, Any] | None = None


def _normalize_reprocess_mode(value: str | None) -> str:
    return "deep" if str(value or "").strip().lower() == "deep" else "fast"


def _reprocess_context_summary(context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    previous = context.get("previous_result")
    if not isinstance(previous, dict):
        previous = {}
    return {
        "mode": _normalize_reprocess_mode(
            context.get("mode") if isinstance(context.get("mode"), str) else None
        ),
        "previous_doc_type": str(previous.get("tipo_documento_detectado") or "").strip() or None,
        "previous_confidence": previous.get("confianza_clasificacion"),
        "previous_requires_review": previous.get("requiere_revision"),
        "previous_recipe_snapshot_id": (
            str(previous.get("recipe_snapshot_id") or "").strip() or None
        ),
        "previous_llm_model": str(previous.get("llm_model") or "").strip() or None,
        "previous_field_count": previous.get("field_count"),
        "missing_fields": [
            str(field).strip()
            for field in (context.get("missing_fields") or [])
            if str(field).strip()
        ],
    }


def _count_detected_scalar_fields(data: dict[str, Any]) -> int:
    ignored_keys = {
        "line_items",
        "filas",
        "filas_por_hoja",
        "metadata_por_hoja",
        "sheet_usada",
        "columnas",
        "columnas_norm",
    }
    count = 0
    for key, value in data.items():
        if key in ignored_keys or str(key).startswith("_"):
            continue
        if isinstance(value, str) and value.strip():
            count += 1
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            count += 1
    return count


def _reprocess_result_changed(
    previous: dict[str, Any] | None,
    *,
    doc_type: str,
    confidence: float,
    requires_review: bool,
    field_count: int,
    field_keys: list[str] | None = None,
) -> bool:
    if not isinstance(previous, dict) or not previous:
        return False
    prev_type = str(previous.get("tipo_documento_detectado") or "").strip()
    prev_conf = previous.get("confianza_clasificacion")
    prev_review = bool(previous.get("requiere_revision"))
    prev_field_count = previous.get("field_count")
    prev_field_keys = [str(key) for key in (previous.get("field_keys") or []) if str(key).strip()]
    if prev_type != str(doc_type or "").strip():
        return True
    try:
        if prev_conf is None or abs(float(prev_conf) - float(confidence)) > 0.001:
            return True
    except (TypeError, ValueError):
        return True
    if prev_review != bool(requires_review):
        return True
    try:
        if prev_field_count is None:
            return True
        if int(prev_field_count) != int(field_count):
            return True
    except (TypeError, ValueError):
        return True
    normalized_field_keys = [str(key) for key in (field_keys or []) if str(key).strip()]
    if prev_field_keys and normalized_field_keys and prev_field_keys != normalized_field_keys:
        return True
    return False


def _load_snapshot(db: Session, snapshot_id: UUID | str | None):
    if not snapshot_id:
        return None
    return recipe_crud.get_snapshot(db, UUID(str(snapshot_id)))


def _build_review_hints(
    db: Session,
    *,
    doc,
    routing_decision: DocumentRoutingDecision | None,
    snapshot_id: UUID | str | None,
) -> list[DocumentReviewHintOut]:
    snapshot = _load_snapshot(db, snapshot_id)
    if snapshot is None:
        return []
    canonical_fields = get_canonical_fields(db, tenant_id=getattr(doc, "tenant_id", None))
    missing_fields = routing_decision.missing_fields if routing_decision else []
    hints = build_snapshot_review_hints(
        snapshot,
        missing_fields=missing_fields,
        canonical_fields=canonical_fields,
        limit=5,
    )
    return [DocumentReviewHintOut.model_validate(item) for item in hints]


async def _analyze_with_context(
    *,
    analyze_document_fn: AnalyzeDocumentFn,
    content: str,
    filename: str,
    format_hint: str,
    has_structured_rows: bool,
    recipe_config: dict[str, Any] | None,
    structured_data: Any | None = None,
    structured_metadata: dict[str, Any] | None = None,
    vision_image_bytes: bytes | bytearray | None,
    fallback_patterns: dict[str, Any],
    canonical_fields: dict[str, Any],
    prompt_config: dict[str, Any],
    db: Any = None,
    reprocess_mode: str = "fast",
    bypass_cache: bool = False,
    deep_reprocess_context: dict[str, Any] | None = None,
    deep_focus_fields: list[str] | None = None,
) -> dict[str, Any]:
    # Si el OCR ya extrajo texto suficiente, no usar visión.
    # La visión solo aplica a imágenes puras o PDFs sin texto extraíble.
    processing_cfg = load_processing_runtime_config(db)
    min_chars = max(1, int(processing_cfg.get("ocr_text_sufficient_min_chars") or 100))

    content_text = (content or "").strip()
    text_is_sufficient = len(content_text) >= min_chars
    structured_is_usable = bool(has_structured_rows or structured_data)

    quality_warning: dict[str, Any] | None = None
    image_bytes = None if text_is_sufficient else bytes(vision_image_bytes) if vision_image_bytes else None

    if vision_image_bytes:
        ai_runtime = load_ai_runtime_config(db)
        quality = _estimate_text_quality(content_text, ai_runtime=ai_runtime)
        quality_threshold = float(
            ai_runtime.get("openai_fallback_ocr_quality_threshold")
            or ai_runtime.get("ocr_min_quality")
            or 0.45
        )
        low_quality = quality["score"] <= quality_threshold

        if low_quality:
            quality_warning = {
                "quality_gate": "warning",
                "quality_score": quality["score"],
                "quality_threshold": quality_threshold,
                "chars": quality["chars"],
                "text_is_sufficient": text_is_sufficient,
                "structured_is_usable": structured_is_usable,
                "degraded_to_review": text_is_sufficient or structured_is_usable or reprocess_mode == "fast",
                "rejected_for_quality": False,
            }

            # Solo en el caso realmente extremo: sin texto útil, sin estructura y en deep mode.
            if not text_is_sufficient and not structured_is_usable and reprocess_mode == "deep":
                quality_warning["quality_gate"] = "rejected"
                quality_warning["degraded_to_review"] = False
                quality_warning["rejected_for_quality"] = True
                raise ValueError(
                    "Imagen de mala calidad: no se pudo extraer texto con suficiente confianza. "
                    "Sube una nueva imagen más nítida, con mejor luz y sin cortes."
                )

            logger.info(
                "quality_gate=degraded_to_review filename=%s score=%.3f threshold=%.3f chars=%s text_is_sufficient=%s structured_is_usable=%s mode=%s",
                filename,
                float(quality["score"]),
                quality_threshold,
                quality["chars"],
                text_is_sufficient,
                structured_is_usable,
                reprocess_mode,
            )

    fast_mode_skip_ai = (
        str(reprocess_mode or "").strip().lower() == "fast"
        and not has_structured_rows
        and text_is_sufficient
    )
    if fast_mode_skip_ai:
        logger.info(
            "fast_mode_skip_ai_due_to_sufficient_text=true filename=%s mode=%s text_is_sufficient=%s reason=fast_mode_text_sufficient_skip",
            filename,
            reprocess_mode,
            text_is_sufficient,
        )
        analysis = {
            "doc_type": "OTHER",
            "confidence": 0.2,
            "reasoning": "Skipped heavy AI extraction in fast mode because OCR text is sufficient.",
            "is_table": False,
            "columns": [],
            "fields": {},
            "raw_response": "reason=fast_mode_text_sufficient_skip",
            "model_used": "fast-mode-skip",
            "analysis_path": "fast_mode_text_sufficient_skip",
            "requires_review": True,
            "fast_mode_skip_ai_due_to_sufficient_text": True,
        }
    else:
        analysis = await analyze_document_fn(
            content,
            filename,
            format_hint,
            has_structured_rows=has_structured_rows,
            recipe_config=recipe_config,
            structured_data=structured_data,
            structured_metadata=structured_metadata,
            image_bytes=image_bytes,
            fallback_patterns=fallback_patterns,
            canonical_fields=canonical_fields,
            prompt_config=prompt_config,
            db=db,
            reprocess_mode=reprocess_mode,
            bypass_cache=bypass_cache,
            deep_reprocess_context=deep_reprocess_context,
            deep_focus_fields=deep_focus_fields,
        )

    if quality_warning:
        analysis.setdefault("warnings", [])
        analysis["warnings"].append(quality_warning)
        analysis["requires_review"] = True

        current_confidence = analysis.get("confidence")
        if current_confidence is None:
            analysis["confidence"] = 0.35
        else:
            try:
                analysis["confidence"] = min(float(current_confidence), 0.35)
            except (TypeError, ValueError):
                analysis["confidence"] = 0.35

    return analysis


async def process_import_document(
    *,
    mode: ProcessingMode,
    db: Session,
    doc,
    tenant_id: UUID,
    user_id: str | None,
    file_bytes: bytes,
    filename: str,
    tipo_archivo: str,
    force: bool,
    extract_text_fn: ExtractTextFn,
    analyze_document_fn: AnalyzeDocumentFn,
    recipe_context: RecipeContext | None = None,
) -> DocumentProcessingResult:
    if mode == "run":
        return await _process_run_document(
            db=db,
            doc=doc,
            tenant_id=tenant_id,
            user_id=user_id,
            file_bytes=file_bytes,
            filename=filename,
            tipo_archivo=tipo_archivo,
            force=force,
            extract_text_fn=extract_text_fn,
            analyze_document_fn=analyze_document_fn,
            recipe_context=recipe_context or RecipeContext(),
        )
    return await _process_async_document(
        mode=mode,
        db=db,
        doc=doc,
        tenant_id=tenant_id,
        user_id=user_id,
        file_bytes=file_bytes,
        filename=filename,
        tipo_archivo=tipo_archivo,
        force=force,
        extract_text_fn=extract_text_fn,
        analyze_document_fn=analyze_document_fn,
        recipe_context=recipe_context or RecipeContext(),
    )


async def _process_async_document(
    *,
    mode: Literal["async"],
    db: Session,
    doc,
    tenant_id: UUID,
    user_id: str | None,
    file_bytes: bytes,
    filename: str,
    tipo_archivo: str,
    force: bool,
    extract_text_fn: ExtractTextFn,
    analyze_document_fn: AnalyzeDocumentFn,
    recipe_context: RecipeContext,
) -> DocumentProcessingResult:
    processing_started_at = time.perf_counter()
    stage_timings: dict[str, int] = {}
    reprocess_mode = _normalize_reprocess_mode(recipe_context.reprocess_mode)
    deep_reprocess = reprocess_mode == "deep"
    force_clean_reimport = bool(recipe_context.force_clean_reimport or deep_reprocess)
    extraction_started_at = time.perf_counter()
    extraction = await extract_text_fn(file_bytes, filename, bypass_cache=deep_reprocess)
    _set_stage_timing(stage_timings, "ocr_extract", extraction_started_at)
    text = extraction.get("text", "")
    structured = extraction.get("structured_data")
    sheet_profiles = extraction.get("sheet_profiles")
    sheet_metadata = extraction.get("sheet_metadata")
    processing_cfg = load_processing_runtime_config(db)
    _field_aliases_for_pre = get_field_aliases(db, tenant_id=tenant_id)

    file_format = str(extraction.get("format", tipo_archivo) or tipo_archivo).upper()
    has_structured = bool(
        structured is not None
        and file_format in {"CSV", "EXCEL", "JSON"}
        and ((isinstance(structured, list) and bool(structured)) or isinstance(structured, dict))
    )

    headers_norm: list[str] = []
    headers_display: list[str] = []
    if isinstance(sheet_profiles, dict) and sheet_profiles:
        for profile in sheet_profiles.values():
            headers_norm = profile.get("headers_norm") or []
            headers_display = profile.get("headers") or headers_norm
            break

    resolved_snapshot_id = recipe_context.resolved_snapshot_id
    resolution_mode = recipe_context.resolution_mode or "zero_shot"
    explicit_recipe_context = recipe_context.explicit_recipe_context and not force_clean_reimport
    if force_clean_reimport:
        resolved_snapshot_id = None
    if not resolved_snapshot_id and not force_clean_reimport:
        existing_snapshot_id = getattr(doc, "recipe_snapshot_id", None)
        if existing_snapshot_id:
            resolved_snapshot_id = existing_snapshot_id
            explicit_recipe_context = True
            if resolution_mode == "zero_shot":
                resolution_mode = "snapshot"
    if sheet_profiles and not force_clean_reimport:
        _, auto_snapshot_id, auto_resolution_mode, _, _ = resolve_auto_recipe(
            db,
            tenant_id,
            sheet_profiles,
            user_id,
        )
        resolution_mode = auto_resolution_mode
        if auto_snapshot_id and not resolved_snapshot_id:
            resolved_snapshot_id = auto_snapshot_id

    if explicit_recipe_context and recipe_context.resolved_snapshot_id:
        resolved_snapshot_id = recipe_context.resolved_snapshot_id

    if has_structured:
        preview_rows = max(1, int(processing_cfg.get("structured_preview_rows") or 5))
        preview_fields = max(1, int(processing_cfg.get("structured_preview_fields") or 8))
        sample_lines = [f"Columnas: {headers_display}"]
        for row in structured[:preview_rows] if isinstance(structured, list) else []:
            if isinstance(row, dict):
                sample_lines.append(
                    str(
                        {
                            k: v
                            for k, v in list(row.items())[:preview_fields]
                            if not k.startswith("_")
                        }
                    )
                )
        llm_content = "\n".join(sample_lines)
    else:
        llm_preview_chars = max(1, int(processing_cfg.get("llm_text_preview_chars") or 6000))
        llm_content = text[:llm_preview_chars] if text else ""

    vision_image_bytes = extraction.get("vision_image_bytes")
    if not isinstance(vision_image_bytes, (bytes, bytearray)):
        vision_image_bytes = file_bytes if tipo_archivo in ("JPG", "PNG", "IMG") else None

    recipe_snapshot = None
    recipe_config: dict[str, Any] = {}
    cached_analysis = None
    text_cached_analysis = None
    analysis_recipe_config: dict[str, Any] = {}
    recipe_resolution_started_at = time.perf_counter()
    if resolved_snapshot_id:
        recipe_snapshot = _load_snapshot(db, resolved_snapshot_id)
        if recipe_snapshot and isinstance(recipe_snapshot.content_json, dict):
            recipe_config = _snapshot_recipe_config(recipe_snapshot)
        if has_structured:
            cached_analysis = get_snapshot_learning(recipe_snapshot, structured_only=True)
        else:
            text_cached_analysis = get_snapshot_learning(recipe_snapshot, structured_only=False)

    recipe_config = build_signal_learning_recipe_config(
        db,
        tenant_id=tenant_id,
        source_doc_type=None,
        base_recipe_config=recipe_config,
    )
    signal_learning_meta = recipe_config.get("_signal_learning") if recipe_config else None
    learning_rerun_summary = None
    _set_stage_timing(stage_timings, "recipe_resolution", recipe_resolution_started_at)

    runtime_config_started_at = time.perf_counter()
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    prompt_config = load_prompt_config(db)
    fallback_patterns = load_doc_type_patterns(db)
    classification_threshold = load_classification_threshold(db)
    learning_ctrl = load_learning_control(db)
    _set_stage_timing(stage_timings, "runtime_config_load", runtime_config_started_at)

    if not has_structured and text.strip():
        file_format = str(extraction.get("format", tipo_archivo) or tipo_archivo).upper()
        if file_format in {"PDF", "PDF_OCR", "IMAGE_OCR"}:
            try:
                table_preview = extract_line_items_table_preview_from_text(
                    text,
                    _field_aliases_for_pre,
                    pdf_config=load_pdf_table_parse_config(db),
                    page_texts=extraction.get("page_texts"),
                )
                if table_preview:
                    preview_rows = max(1, int(processing_cfg.get("structured_preview_rows") or 5))
                    preview_content = _build_table_prompt_preview(
                        table_preview,
                        max_rows=preview_rows,
                    )
                    if preview_content:
                        llm_content = preview_content
            except Exception:
                logger.debug("No se pudo construir preview tabular OCR", exc_info=True)

    # ── Pre-classification: attempt to resolve doc_type without AI ──────────────
    pre_classify_started_at = time.perf_counter()
    _pre_cfg = load_pre_classifier_config(db)
    _structured_skip_threshold = float(_pre_cfg.get("structured_skip_threshold", 0.75))

    pre_class: PreClassResult | None = classify_before_ai(
        db=db,
        filename=filename,
        headers_norm=headers_norm,
        field_aliases=_field_aliases_for_pre,
        cached_analysis=cached_analysis,
        config=_pre_cfg,
        ocr_text=text if not has_structured else None,
        tenant_id=tenant_id,
        tipo_archivo=tipo_archivo,
    )
    _set_stage_timing(stage_timings, "pre_classify", pre_classify_started_at)

    if pre_class and pre_class.skip_ai:
        if pre_class.layer == "template":
            # L5: Template extraction — campos extraídos directamente, sin AI
            analysis = {
                **(pre_class.cached_analysis or {}),
                "model_used": "pre-classifier/template",
                "prompt_sent": "",
                "raw_response": pre_class.reasoning,
            }
        else:
            # L1: Snapshot cache — full result, no AI call
            analysis = {
                **(pre_class.cached_analysis or {}),
                "fields": {},
                "is_table": True,
                "columns": [],
                "model_used": f"pre-classifier/{pre_class.layer}",
                "prompt_sent": "",
                "raw_response": pre_class.reasoning,
            }
    elif pre_class and has_structured and pre_class.confidence >= _structured_skip_threshold:
        # L2/L3: Structured doc with confident pre-classification — skip CLASSIFICATION AI call
        analysis = {
            "doc_type": pre_class.doc_type,
            "confidence": pre_class.confidence,
            "reasoning": pre_class.reasoning,
            "is_table": True,
            "columns": headers_display,
            "fields": {},
            "model_used": f"pre-classifier/{pre_class.layer}",
            "prompt_sent": "",
            "raw_response": pre_class.reasoning,
        }
    else:
        # Inject pre-classifier hint so AI skips classification guesswork.
        # Exception: never inject table-only type hints (INVENTORY, PRICE_LIST, etc.)
        # for non-structured docs (PDFs, images) — those types require spreadsheet rows
        # that a PDF can never provide, causing datos_extraidos to be always empty.
        table_only_doc_types = _runtime_doc_type_set(processing_cfg, "table_only_doc_types")
        doc_type_hint_min_confidence = float(
            processing_cfg.get("doc_type_hint_min_confidence") or 0.65
        )
        _rc_for_ai = dict(recipe_config) if recipe_config else {}
        if pre_class and pre_class.confidence >= doc_type_hint_min_confidence:
            _hint_type = pre_class.doc_type.upper()
            if has_structured or _hint_type not in table_only_doc_types:
                _rc_for_ai["doc_type_hint"] = pre_class.doc_type
                _rc_for_ai["doc_type_hint_confidence"] = pre_class.confidence
        if not has_structured and text_cached_analysis and not _rc_for_ai.get("doc_type_hint"):
            _cached_type = str(text_cached_analysis.get("doc_type") or "").upper()
            _cached_conf = float(text_cached_analysis.get("confidence") or 0)
            if (
                _cached_type
                and _cached_type != "OTHER"
                and _cached_conf >= doc_type_hint_min_confidence
            ):
                if _cached_type not in table_only_doc_types:
                    _rc_for_ai["doc_type_hint"] = _cached_type
                    _rc_for_ai["doc_type_hint_confidence"] = _cached_conf
        analysis_recipe_config = dict(_rc_for_ai)
        ai_primary_started_at = time.perf_counter()
        analysis = await _analyze_with_context(
            analyze_document_fn=analyze_document_fn,
            content=llm_content,
            filename=filename,
            format_hint=extraction.get("format", tipo_archivo),
            has_structured_rows=has_structured,
            recipe_config=_rc_for_ai,
            structured_data=structured if has_structured else None,
            structured_metadata=(sheet_profiles if has_structured else sheet_metadata),
            vision_image_bytes=vision_image_bytes,
            fallback_patterns=fallback_patterns,
            canonical_fields=canonical_fields,
            prompt_config=prompt_config,
            db=db,
            reprocess_mode=reprocess_mode,
            bypass_cache=deep_reprocess,
            deep_reprocess_context=recipe_context.reprocess_context,
            deep_focus_fields=(
                _reprocess_context_summary(recipe_context.reprocess_context).get("missing_fields")
                if deep_reprocess
                else None
            ),
        )
        _set_stage_timing(stage_timings, "ai_primary", ai_primary_started_at)

    # Attach pre-classification metadata for learning at confirm time
    if pre_class:
        analysis.setdefault(
            "_pre_class",
            {
                "layer": pre_class.layer,
                "doc_type": pre_class.doc_type,
                "confidence": pre_class.confidence,
            },
        )

    normalize_analysis_started_at = time.perf_counter()
    normalized_analysis = _normalize_analysis_output(analysis)
    _set_stage_timing(stage_timings, "analysis_normalize", normalize_analysis_started_at)
    tipo_doc = str(normalized_analysis["doc_type"])
    confianza = float(normalized_analysis["confidence"])
    requiere_revision = confianza < classification_threshold
    razonamiento = str(normalized_analysis["reasoning"])
    analysis_fields = normalized_analysis["fields"]
    current_field_keys = (
        sorted(
            str(key)
            for key, value in analysis_fields.items()
            if not str(key).startswith("_") and value not in (None, "", [], {})
        )
        if isinstance(analysis_fields, dict)
        else []
    )
    reprocess_context_summary = _reprocess_context_summary(recipe_context.reprocess_context)
    previous_result = recipe_context.reprocess_context.get("previous_result")
    current_field_count = (
        _count_detected_scalar_fields(analysis_fields) if isinstance(analysis_fields, dict) else 0
    )
    reprocess_result_changed = _reprocess_result_changed(
        previous_result if isinstance(previous_result, dict) else None,
        doc_type=tipo_doc,
        confidence=confianza,
        requires_review=requiere_revision,
        field_count=current_field_count,
        field_keys=current_field_keys,
    )

    if recipe_snapshot:
        remember_snapshot_learning(
            db,
            recipe_snapshot,
            {
                "doc_type": tipo_doc,
                "confidence": confianza,
                "reasoning": razonamiento,
            },
            structured_only=has_structured,
        )

    crud.add_log(
        db,
        doc.id,
        "CLASSIFY",
        user_id,
        {
            "tipo_documento": tipo_doc,
            "confianza": confianza,
            "razonamiento": razonamiento,
            "model_used": analysis.get("model_used"),
        },
    )

    _used_text_fallback = False
    if has_structured:
        structured_output_limit = max(
            1, int(processing_cfg.get("structured_output_rows_limit") or 200)
        )
        sheet_used = extraction.get("sheet_used")
        sheet_metadata = extraction.get("sheet_metadata") or {}
        filas_por_hoja: dict[str, list] = {}
        for row in structured or []:
            if isinstance(row, dict):
                sheet_name = str(row.get("_sheet") or sheet_used or "")
                if sheet_name:
                    filas_por_hoja.setdefault(sheet_name, []).append(row)
        datos_extraidos = {
            "filas": structured[:structured_output_limit],
            "total_filas": len(structured),
            "columnas": headers_display or headers_norm,
            "columnas_norm": headers_norm,
            "filas_por_hoja": filas_por_hoja,
            "metadata_por_hoja": sheet_metadata,
            "sheet_usada": sheet_used,
        }
        product_like_doc_types = _runtime_doc_type_set(processing_cfg, "product_like_doc_types")
        if (
            looks_like_product_document(
                datos_extraidos,
                sheet_name=sheet_used,
                detection_config=load_product_sheet_detection_config(db),
            )
            and tipo_doc not in product_like_doc_types
        ):
            tipo_doc = "INVENTORY"
            requiere_revision = True
            crud.add_log(
                db,
                doc.id,
                "CLASSIFY_OVERRIDE",
                user_id,
                {
                    "reason": "product_sheet_detection",
                    "tipo_documento": tipo_doc,
                    "sheet": sheet_used,
                },
            )
    else:
        datos_extraidos = analysis_fields or {}
        # Text fallback: when AI failed and OCR text is available, extract
        # fields using DB-configured labels and aliases.
        if text.strip() and _analysis_indicates_ai_failure(
            analysis,
            processing_cfg=processing_cfg,
        ):
            text_fallback_started_at = time.perf_counter()
            # El timeout de la IA puede haber dejado la transacción en estado abortado.
            # Hacemos rollback para limpiarla antes de continuar con queries al DB.
            try:
                db.rollback()
            except Exception:
                pass
            field_aliases = get_field_aliases(db, tenant_id=tenant_id)
            amount_labels = load_amount_label_config(db)
            pdf_config = load_pdf_table_parse_config(db)
            # Auto-learn new aliases from OCR labels before extraction
            try:
                learned = learn_labels_from_text(
                    db,
                    text,
                    canonical_fields,
                    field_aliases,
                    amount_labels,
                )
                if learned:
                    from .field_alias_loader import invalidate_cache

                    invalidate_cache()
                    field_aliases = get_field_aliases(db, tenant_id=tenant_id)
            except Exception as exc:
                logger.debug("Auto-learn aliases error (non-fatal): %s", exc)

            fallback_fields = extract_fields_from_text(
                text,
                canonical_fields=canonical_fields,
                field_aliases=field_aliases,
                amount_labels=amount_labels,
                pdf_config=pdf_config,
                page_texts=extraction.get("page_texts"),
            )
            fallback_fields = _sanitize_text_fallback_fields(
                fallback_fields,
                content=text,
                format_hint=str(extraction.get("format", tipo_archivo) or tipo_archivo),
                prompt_config=prompt_config,
                ai_runtime=load_ai_runtime_config(db),
                ocr_runtime=load_ocr_runtime_config(db),
            )
            if fallback_fields:
                if not datos_extraidos:
                    datos_extraidos = fallback_fields
                else:
                    _merge_text_fallback_fields(datos_extraidos, fallback_fields)
                requiere_revision = True
                _used_text_fallback = True
            else:
                logger.info(
                    "text_fallback_result=empty_after_sanitize filename=%s mode=%s quality_hint=%s",
                    filename,
                    reprocess_mode,
                    "low_or_noisy_ocr",
                )
            _set_stage_timing(stage_timings, "text_fallback", text_fallback_started_at)

        if tipo_doc != "OTHER" and not explicit_recipe_context:
            auto_recipe_started_at = time.perf_counter()
            auto_recipe_config, post_snapshot_id, _, auto_recipe_created, _ = (
                resolve_auto_recipe_from_text(
                    db,
                    tenant_id,
                    tipo_doc,
                    datos_extraidos,
                    extraction.get("format", tipo_archivo),
                    user_id,
                    force_new=force,
                )
            )
            _set_stage_timing(stage_timings, "auto_recipe_resolution", auto_recipe_started_at)
            if post_snapshot_id:
                resolved_snapshot_id = post_snapshot_id
                recipe_snapshot = _load_snapshot(db, post_snapshot_id)
                remember_snapshot_learning(
                    db,
                    recipe_snapshot,
                    {
                        "doc_type": tipo_doc,
                        "confidence": confianza,
                        "reasoning": razonamiento,
                    },
                    structured_only=False,
                )
            _snapshot_learning_version = get_snapshot_learning_version(recipe_snapshot)
            _first_pass_had_learning = bool(
                analysis_recipe_config.get("field_descriptions")
                or analysis_recipe_config.get("prompt_user")
            )
            _learning_mature = (
                _first_pass_had_learning
                and _snapshot_learning_version >= 2
                and confianza >= classification_threshold
            )
            _rerun_allowed = bool(learning_ctrl.get("rerun_enabled", True)) and float(
                confianza or 0.0
            ) >= float(learning_ctrl.get("rerun_min_confidence", 0.0))
            if (
                auto_recipe_config
                and not auto_recipe_created
                and not _learning_mature
                and _rerun_allowed
            ):
                baseline_routing = build_document_routing_decision(
                    source_doc_type=tipo_doc,
                    ai_confidence=confianza,
                    extracted_data=analysis_fields if isinstance(analysis_fields, dict) else {},
                    canonical_document={},
                    category_keywords=get_doc_categories(db),
                    requires_review=requiere_revision,
                    db=db,
                    tenant_id=tenant_id,
                )
                rerun_recipe_config = build_signal_learning_recipe_config(
                    db,
                    tenant_id=tenant_id,
                    source_doc_type=tipo_doc,
                    document_type_hint=baseline_routing.document_type,
                    base_recipe_config=auto_recipe_config,
                )
                if should_run_learning_rerun(
                    baseline_confidence=confianza,
                    classification_threshold=classification_threshold,
                    baseline_fields=analysis_fields if isinstance(analysis_fields, dict) else {},
                    baseline_routing=baseline_routing,
                    base_recipe_config=analysis_recipe_config,
                    candidate_recipe_config=rerun_recipe_config,
                ):
                    ai_rerun_started_at = time.perf_counter()
                    rerun_analysis = await _analyze_with_context(
                        analyze_document_fn=analyze_document_fn,
                        content=llm_content,
                        filename=filename,
                        format_hint=extraction.get("format", tipo_archivo),
                        has_structured_rows=False,
                        recipe_config=rerun_recipe_config,
                        structured_data=None,
                        structured_metadata=None,
                        vision_image_bytes=vision_image_bytes,
                        fallback_patterns=fallback_patterns,
                        canonical_fields=canonical_fields,
                        prompt_config=prompt_config,
                        db=db,
                        reprocess_mode=reprocess_mode,
                        bypass_cache=deep_reprocess,
                        deep_reprocess_context=recipe_context.reprocess_context,
                        deep_focus_fields=(
                            _reprocess_context_summary(recipe_context.reprocess_context).get(
                                "missing_fields"
                            )
                            if deep_reprocess
                            else None
                        ),
                    )
                    _set_stage_timing(stage_timings, "ai_rerun", ai_rerun_started_at)
                    rerun_normalized = _normalize_analysis_output(rerun_analysis)
                    rerun_fields = rerun_normalized["fields"]
                    if isinstance(rerun_fields, dict) and rerun_fields:
                        rerun_routing = build_document_routing_decision(
                            source_doc_type=str(rerun_normalized["doc_type"]),
                            ai_confidence=float(rerun_normalized["confidence"]),
                            extracted_data=rerun_fields,
                            canonical_document={},
                            category_keywords=get_doc_categories(db),
                            requires_review=(
                                float(rerun_normalized["confidence"]) < classification_threshold
                            ),
                            db=db,
                            tenant_id=tenant_id,
                        )
                        learning_rerun_summary = summarize_learning_rerun(
                            baseline_doc_type=tipo_doc,
                            baseline_confidence=confianza,
                            baseline_fields=(
                                analysis_fields if isinstance(analysis_fields, dict) else {}
                            ),
                            baseline_routing=baseline_routing.model_dump(mode="json"),
                            rerun_doc_type=str(rerun_normalized["doc_type"]),
                            rerun_confidence=float(rerun_normalized["confidence"]),
                            rerun_fields=rerun_fields,
                            rerun_routing=rerun_routing.model_dump(mode="json"),
                            signal_learning_meta=(
                                rerun_recipe_config.get("_signal_learning")
                                if isinstance(rerun_recipe_config, dict)
                                else None
                            ),
                        )
                        analysis = rerun_analysis
                        normalized_analysis = rerun_normalized
                        tipo_doc = str(rerun_normalized["doc_type"])
                        confianza = float(rerun_normalized["confidence"])
                        requiere_revision = confianza < classification_threshold
                        razonamiento = str(rerun_normalized["reasoning"])
                        analysis_fields = rerun_fields
                        datos_extraidos = rerun_fields
                        recipe_config = auto_recipe_config

    crud.add_log(
        db,
        doc.id,
        "EXTRACT",
        user_id,
        {
            "campos_extraidos": (
                list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
            ),
            "reprocess_mode": reprocess_mode,
            "reprocess_cache_hit": bool(analysis.get("cache_hit")),
            "reprocess_cache_bypassed": bool(analysis.get("cache_bypassed")),
            "reprocess_result_changed": reprocess_result_changed,
            "reprocess_missing_fields": reprocess_context_summary.get("missing_fields", []),
        },
    )

    datos_extraidos = (
        _json_safe(datos_extraidos)
        if isinstance(datos_extraidos, (dict, list))
        else datos_extraidos
    )
    sheet_profiles = (
        _json_safe(sheet_profiles) if isinstance(sheet_profiles, (dict, list)) else sheet_profiles
    )
    postprocess_started_at = time.perf_counter()
    field_aliases = get_field_aliases(db, tenant_id=tenant_id)
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    if isinstance(datos_extraidos, dict):
        unmapped_cols = _normalize_line_item_extra_columns(datos_extraidos, field_aliases)
        _project_line_item_slots(datos_extraidos, canonical_fields)
        if unmapped_cols:
            try:
                _learn_column_candidates(
                    db,
                    col_names=unmapped_cols,
                    doc_type=tipo_doc,
                    tenant_id=tenant_id,
                    field_aliases=field_aliases,
                    canonical_fields=canonical_fields,
                )
            except Exception as exc:
                logger.debug("Column candidate learning error (non-fatal): %s", exc)
    canonical_document, projection = build_document_projection(
        datos_extraidos if isinstance(datos_extraidos, dict) else {},
        doc_type=tipo_doc,
        source_format=extraction.get("format", tipo_archivo),
        field_aliases=field_aliases,
        canonical_fields=canonical_fields,
    )
    _set_stage_timing(stage_timings, "postprocess_projection", postprocess_started_at)
    current_snapshot = recipe_snapshot
    if current_snapshot is None and resolved_snapshot_id:
        current_snapshot = _load_snapshot(db, resolved_snapshot_id)
    learning_version_applied = get_snapshot_learning_version(current_snapshot)
    model_used = (analysis.get("model_used") or "unknown") + (
        "+text-fallback" if _used_text_fallback else ""
    )
    raw_ai_json = _json_safe(
        {
            "run": {
                "recipe_resolution": {
                    "used": resolution_mode,
                    "recipe_snapshot_id": (
                        str(resolved_snapshot_id) if resolved_snapshot_id else None
                    ),
                    "learning_version_applied": learning_version_applied,
                },
                "learning_version_applied": learning_version_applied,
                "model": model_used,
                "signal_learning": signal_learning_meta,
                "learning_rerun": learning_rerun_summary,
                "pre_classification": analysis.get("_pre_class"),
                "headers_norm": headers_norm,
                "reprocess": {
                    "mode": reprocess_mode,
                    "deep": deep_reprocess,
                    "ocr_cache_hit": bool(extraction.get("_cache_hit")),
                    "ocr_cache_bypassed": bool(extraction.get("_cache_bypassed")),
                    "ai_cache_hit": bool(analysis.get("cache_hit")),
                    "ai_cache_bypassed": bool(analysis.get("cache_bypassed")),
                    "result_changed": reprocess_result_changed,
                    "context": reprocess_context_summary,
                },
            },
            "analysis": {
                "prompt": analysis.get("prompt_sent", ""),
                "raw_response": analysis.get("raw_response", ""),
                "parsed": {
                    "tipo_documento": tipo_doc,
                    "confianza": confianza,
                    "razonamiento": razonamiento,
                },
                "campos_extraidos": (
                    list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
                ),
            },
            "canonical_document": canonical_document,
        }
    )
    routing_started_at = time.perf_counter()
    routing_decision = build_document_routing_decision(
        source_doc_type=tipo_doc,
        ai_confidence=confianza,
        extracted_data=datos_extraidos if isinstance(datos_extraidos, dict) else {},
        canonical_document=canonical_document,
        category_keywords=get_doc_categories(db),
        requires_review=requiere_revision,
        db=db,
        tenant_id=tenant_id,
    )
    _set_stage_timing(stage_timings, "routing", routing_started_at)
    raw_ai_json["routing"] = routing_decision.model_dump(mode="json")

    # Detect AI timeout / empty extraction for unstructured docs
    ai_raw_response = str(analysis.get("raw_response", "") or "")
    ai_timeout_error = None
    if (
        not has_structured
        and isinstance(datos_extraidos, dict)
        and not datos_extraidos
        and ("timeout" in ai_raw_response.lower() or "unavailable" in ai_raw_response.lower())
    ):
        ai_timeout_error = ai_raw_response

    staging_started_at = time.perf_counter()
    if isinstance(datos_extraidos, dict):
        upsert_staging_lines_from_extraction(db, doc.id, tenant_id, datos_extraidos)
    _set_stage_timing(stage_timings, "staging_sync", staging_started_at)

    review_hints_started_at = time.perf_counter()
    review_hints = _build_review_hints(
        db,
        doc=doc,
        routing_decision=routing_decision,
        snapshot_id=resolved_snapshot_id,
    )
    _set_stage_timing(stage_timings, "review_hints", review_hints_started_at)
    raw_ai_json["run"].update(
        _build_timing_summary(stage_timings=stage_timings, started_at=processing_started_at)
    )

    document_update_started_at = time.perf_counter()
    crud.update_documento(
        db,
        doc,
        {
            "texto_ocr": text[
                : max(1, int(processing_cfg.get("persist_text_ocr_max_chars") or 50000))
            ],
            "tipo_documento_detectado": tipo_doc,
            "confianza_clasificacion": confianza,
            "requiere_revision": routing_decision.needs_human_review,
            "datos_extraidos": datos_extraidos,
            "estado": "REVIEW",
            "error_detalle": ai_timeout_error,
            **projection,
            "fingerprint_json": sheet_profiles,
            "sheet_profiles_json": sheet_profiles,
            "llm_model": model_used,
            "raw_ai_json": raw_ai_json,
            "recipe_snapshot_id": resolved_snapshot_id,
        },
    )
    _set_stage_timing(stage_timings, "document_update", document_update_started_at)
    raw_ai_json["run"].update(
        _build_timing_summary(stage_timings=stage_timings, started_at=processing_started_at)
    )
    crud.update_documento(db, doc, {"raw_ai_json": raw_ai_json})
    logger.info(
        "importador.processing.completed doc_id=%s mode=%s metrics=%s",
        doc.id,
        mode,
        _json_safe(
            {
                "tenant_id": str(tenant_id),
                "doc_type": tipo_doc,
                "model": model_used,
                **raw_ai_json["run"],
            }
        ),
    )
    return DocumentProcessingResult(
        tipo_documento_detectado=tipo_doc,
        confianza_clasificacion=confianza,
        requiere_revision=routing_decision.needs_human_review,
        datos_extraidos=datos_extraidos if isinstance(datos_extraidos, dict) else None,
        llm_model=model_used,
        recipe_snapshot_id=resolved_snapshot_id,
        recipe_used=resolution_mode,
        routing_decision=routing_decision,
        review_hints=review_hints,
        raw_ai_json=raw_ai_json,
    )


async def _process_run_document(
    *,
    db: Session,
    doc,
    tenant_id: UUID,
    user_id: str | None,
    file_bytes: bytes,
    filename: str,
    tipo_archivo: str,
    force: bool,
    extract_text_fn: ExtractTextFn,
    analyze_document_fn: AnalyzeDocumentFn,
    recipe_context: RecipeContext,
) -> DocumentProcessingResult:
    processing_started_at = time.perf_counter()
    stage_timings: dict[str, int] = {}
    reprocess_mode = _normalize_reprocess_mode(recipe_context.reprocess_mode)
    deep_reprocess = reprocess_mode == "deep"
    force_clean_reimport = bool(recipe_context.force_clean_reimport or deep_reprocess)
    extraction_started_at = time.perf_counter()
    extraction = await extract_text_fn(file_bytes, filename, bypass_cache=deep_reprocess)
    _set_stage_timing(stage_timings, "ocr_extract", extraction_started_at)
    text = extraction.get("text", "")
    structured = extraction.get("structured_data")
    sheet_profiles = extraction.get("sheet_profiles")
    sheet_metadata = extraction.get("sheet_metadata") or {}
    sheet_used = extraction.get("sheet_used")
    processing_cfg = load_processing_runtime_config(db)

    has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)
    structured_rows_all: list[dict[str, Any]] = structured if isinstance(structured, list) else []
    structured_rows: list[dict[str, Any]] = list(structured_rows_all)

    headers_norm: list[str] = []
    headers_display: list[str] = []
    if has_structured:
        structured_output_limit = max(
            1, int(processing_cfg.get("structured_output_rows_limit") or 200)
        )
        sheet_names = list(sheet_profiles.keys()) if sheet_profiles else []
        if sheet_used is None and sheet_names:
            sheet_used = sheet_names[0]
        if sheet_used and structured_rows:
            filtered_rows = [
                row
                for row in structured_rows
                if isinstance(row, dict) and row.get("_sheet") == sheet_used
            ]
            if filtered_rows:
                structured_rows = filtered_rows
        if sheet_profiles:
            profile = sheet_profiles.get(sheet_used) or (
                sheet_profiles[sheet_names[0]] if sheet_names else None
            )
            if profile:
                headers_norm = profile.get("headers_norm") or []
                headers_display = profile.get("headers") or headers_norm

    recipe_resolution_started_at = time.perf_counter()
    local_recipe_config = dict(recipe_context.recipe_config or {})
    local_resolution = (
        "force_clean"
        if force_clean_reimport and not local_recipe_config
        else recipe_context.resolution_mode
    )
    local_snapshot_id = (
        None
        if force_clean_reimport and not local_recipe_config
        else recipe_context.resolved_snapshot_id
    )
    if local_snapshot_id and not local_recipe_config:
        snapshot = _load_snapshot(db, local_snapshot_id)
        if snapshot and isinstance(snapshot.content_json, dict):
            local_recipe_config = _snapshot_recipe_config(snapshot)
    local_auto_created = False
    local_auto_name: str | None = None
    generated_auto_snapshot_id: UUID | None = None
    generated_auto_mode: str | None = None
    if sheet_profiles and not force_clean_reimport and not local_recipe_config:
        auto_rc, auto_snap_id, auto_mode, local_auto_created, local_auto_name = resolve_auto_recipe(
            db, tenant_id, sheet_profiles, user_id, force_new=force
        )
        generated_auto_snapshot_id = auto_snap_id
        generated_auto_mode = auto_mode
        if auto_rc:
            local_recipe_config = auto_rc
            local_resolution = auto_mode
        if auto_snap_id:
            local_snapshot_id = auto_snap_id
    _set_stage_timing(stage_timings, "recipe_resolution", recipe_resolution_started_at)

    recipe_name_detected: str | None = None
    recipe_name_field_candidates = {
        key.lower() for key in _runtime_text_list(processing_cfg, "recipe_name_field_candidates")
    }
    if has_structured:
        preview_rows = max(1, int(processing_cfg.get("structured_preview_rows") or 5))
        preview_fields = max(1, int(processing_cfg.get("structured_preview_fields") or 8))
        sheet_names = list(sheet_profiles.keys()) if sheet_profiles else []
        if sheet_used is None and sheet_names:
            sheet_used = sheet_names[0]
        sample_lines = [f"Columnas: {headers_display}"]
        for row in structured_rows[:preview_rows]:
            if isinstance(row, dict):
                sample_lines.append(
                    str(
                        {
                            k: v
                            for k, v in list(row.items())[:preview_fields]
                            if not k.startswith("_")
                        }
                    )
                )
                if recipe_name_detected is None:
                    for key in row.keys():
                        key_norm = str(key or "").strip().lower()
                        if key_norm in recipe_name_field_candidates:
                            value = row.get(key)
                            if value:
                                recipe_name_detected = str(value).strip()
                                break
        llm_content = "\n".join(sample_lines)
    else:
        llm_preview_chars = max(1, int(processing_cfg.get("llm_text_preview_chars") or 6000))
        llm_content = text[:llm_preview_chars] if text else ""

    is_image_doc = tipo_archivo in ("JPG", "PNG", "IMG")
    is_scanned_pdf = tipo_archivo == "PDF" and extraction.get("format") == "PDF_OCR"
    vision_image_bytes = extraction.get("vision_image_bytes")
    if not isinstance(vision_image_bytes, (bytes, bytearray)):
        vision_image_bytes = file_bytes if is_image_doc else None

    recipe_snapshot = _load_snapshot(db, local_snapshot_id)
    cached_analysis = None
    text_cached_analysis_run = None
    analysis_recipe_config = dict(local_recipe_config or {})
    if recipe_snapshot:
        if has_structured:
            cached_analysis = get_snapshot_learning(recipe_snapshot, structured_only=True)
        else:
            text_cached_analysis_run = get_snapshot_learning(recipe_snapshot, structured_only=False)

    runtime_config_started_at = time.perf_counter()
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    prompt_config = load_prompt_config(db)
    fallback_patterns = load_doc_type_patterns(db)
    classification_threshold = load_classification_threshold(db)
    learning_ctrl = load_learning_control(db)
    _set_stage_timing(stage_timings, "runtime_config_load", runtime_config_started_at)
    if cached_analysis:
        analysis = {
            **cached_analysis,
            "fields": {},
            "is_table": True,
            "columns": [],
            "model_used": "snapshot-cache",
            "prompt_sent": "",
            "raw_response": "snapshot-cache",
        }
    else:
        _rc_for_run = dict(local_recipe_config or {})
        doc_type_hint_min_confidence = float(
            processing_cfg.get("doc_type_hint_min_confidence") or 0.65
        )
        table_only_doc_types = _runtime_doc_type_set(processing_cfg, "table_only_doc_types")
        if text_cached_analysis_run and not _rc_for_run.get("doc_type_hint"):
            _cached_type = str(text_cached_analysis_run.get("doc_type") or "").upper()
            _cached_conf = float(text_cached_analysis_run.get("confidence") or 0)
            if (
                _cached_type
                and _cached_type != "OTHER"
                and _cached_conf >= doc_type_hint_min_confidence
                and (has_structured or _cached_type not in table_only_doc_types)
            ):
                _rc_for_run["doc_type_hint"] = _cached_type
                _rc_for_run["doc_type_hint_confidence"] = _cached_conf
        ai_primary_started_at = time.perf_counter()
        analysis = await analyze_document_fn(
            llm_content,
            filename,
            extraction.get("format", tipo_archivo),
            has_structured_rows=has_structured,
            recipe_config=_rc_for_run,
            structured_data=structured if has_structured else None,
            structured_metadata=sheet_profiles if has_structured else sheet_metadata,
            image_bytes=(
                bytes(vision_image_bytes)
                if (is_image_doc or is_scanned_pdf) and vision_image_bytes
                else None
            ),
            fallback_patterns=fallback_patterns,
            canonical_fields=canonical_fields,
            prompt_config=prompt_config,
            reprocess_mode=reprocess_mode,
            bypass_cache=deep_reprocess,
            deep_reprocess_context=recipe_context.reprocess_context,
            deep_focus_fields=(
                _reprocess_context_summary(recipe_context.reprocess_context).get("missing_fields")
                if deep_reprocess
                else None
            ),
        )
        _set_stage_timing(stage_timings, "ai_primary", ai_primary_started_at)
    normalize_analysis_started_at = time.perf_counter()
    normalized_analysis = _normalize_analysis_output(analysis)
    _set_stage_timing(stage_timings, "analysis_normalize", normalize_analysis_started_at)

    tipo_doc = str(normalized_analysis["doc_type"])
    confianza = float(normalized_analysis["confidence"])
    razonamiento = str(normalized_analysis["reasoning"])
    analysis_fields = normalized_analysis["fields"]
    requiere_revision = confianza < classification_threshold
    current_field_keys = (
        sorted(
            str(key)
            for key, value in analysis_fields.items()
            if not str(key).startswith("_") and value not in (None, "", [], {})
        )
        if isinstance(analysis_fields, dict)
        else []
    )
    reprocess_context_summary = _reprocess_context_summary(recipe_context.reprocess_context)
    previous_result = recipe_context.reprocess_context.get("previous_result")
    current_field_count = (
        _count_detected_scalar_fields(analysis_fields) if isinstance(analysis_fields, dict) else 0
    )
    reprocess_result_changed = _reprocess_result_changed(
        previous_result if isinstance(previous_result, dict) else None,
        doc_type=tipo_doc,
        confidence=confianza,
        requires_review=requiere_revision,
        field_count=current_field_count,
        field_keys=current_field_keys,
    )

    if recipe_snapshot:
        remember_snapshot_learning(
            db,
            recipe_snapshot,
            {
                "doc_type": tipo_doc,
                "confidence": confianza,
                "reasoning": razonamiento,
            },
            structured_only=has_structured,
        )

    if has_structured:
        sheet_names = list(sheet_profiles.keys()) if sheet_profiles else []
        if sheet_used is None and sheet_names:
            sheet_used = sheet_names[0]
        columnas = headers_display or headers_norm
        if recipe_name_detected is None:
            for row in structured_rows[:structured_output_limit]:
                if not isinstance(row, dict):
                    continue
                for key in row.keys():
                    key_norm = str(key or "").strip().lower()
                    if key_norm in recipe_name_field_candidates:
                        value = row.get(key)
                        if value:
                            recipe_name_detected = str(value).strip()
                            break
                if recipe_name_detected:
                    break
        meta_for_sheet = None
        if sheet_metadata:
            meta_for_sheet = sheet_metadata.get(sheet_used) or (
                sheet_metadata.get(sheet_names[0]) if sheet_names else None
            )
        if recipe_name_detected is None and meta_for_sheet:
            for key, value in meta_for_sheet.items():
                key_norm = str(key or "").strip().lower()
                if key_norm in recipe_name_field_candidates and value:
                    recipe_name_detected = str(value).strip()
                    break
        if recipe_name_detected is None:
            recipe_name_detected = (
                sheet_used
                or (list(sheet_profiles.keys())[0] if sheet_profiles else None)
                or Path(filename).stem
            )

        filas_por_hoja: dict[str, list] = {}
        for row in structured_rows_all:
            if not isinstance(row, dict):
                continue
            sheet_name = row.get("_sheet") or sheet_used or ""
            filas_por_hoja.setdefault(str(sheet_name), []).append(row)
        filas_count = {key: len(value) for key, value in filas_por_hoja.items()}

        perfiles_hojas: dict[str, dict[str, Any]] = {}
        for sheet_name in sheet_names:
            prof = sheet_profiles.get(sheet_name) if sheet_profiles else None
            if prof:
                perfiles_hojas[sheet_name] = {
                    "columnas": prof.get("headers") or prof.get("headers_norm") or [],
                    "columnas_norm": prof.get("headers_norm") or [],
                    "total_filas": len(filas_por_hoja.get(sheet_name, [])),
                }

        datos_extraidos = {
            "filas": structured_rows[:structured_output_limit],
            "total_filas": len(structured_rows),
            "columnas": columnas,
            "columnas_norm": headers_norm,
            "nombre_receta": recipe_name_detected,
            "sheet_usada": sheet_used,
            "hojas": sheet_names,
            "perfiles_hojas": perfiles_hojas,
        }
        if meta_for_sheet:
            datos_extraidos["metadata"] = meta_for_sheet
        if filas_por_hoja:
            datos_extraidos["filas_por_hoja"] = {
                key: value[:structured_output_limit] for key, value in filas_por_hoja.items()
            }
            datos_extraidos["filas_por_hoja_count"] = filas_count
        product_like_doc_types = _runtime_doc_type_set(processing_cfg, "product_like_doc_types")
        if (
            looks_like_product_document(
                datos_extraidos,
                sheet_name=sheet_used,
                detection_config=load_product_sheet_detection_config(db),
            )
            and tipo_doc not in product_like_doc_types
        ):
            tipo_doc = "INVENTORY"
            requiere_revision = True
    else:
        datos_extraidos = analysis_fields or {}

    auto_recipe_created = local_auto_created
    auto_recipe_name: str | None = local_auto_name
    if not sheet_profiles and tipo_doc != "OTHER" and not recipe_context.explicit_recipe_context:
        auto_recipe_started_at = time.perf_counter()
        auto_rc2, post_snap_id, _, auto_recipe_created, auto_recipe_name = (
            resolve_auto_recipe_from_text(
                db,
                tenant_id,
                tipo_doc,
                datos_extraidos,
                extraction.get("format", tipo_archivo),
                user_id,
                force_new=force,
            )
        )
        _set_stage_timing(stage_timings, "auto_recipe_resolution", auto_recipe_started_at)
        if post_snap_id and not local_snapshot_id:
            local_snapshot_id = post_snap_id
            _run_snap = _load_snapshot(db, post_snap_id)
            if _run_snap:
                remember_snapshot_learning(
                    db,
                    _run_snap,
                    {
                        "doc_type": tipo_doc,
                        "confidence": confianza,
                        "reasoning": razonamiento,
                    },
                    structured_only=False,
                )
        _run_learning_version = (
            get_snapshot_learning_version(_load_snapshot(db, local_snapshot_id))
            if local_snapshot_id
            else 0
        )
        _run_first_pass_had_learning = bool(
            analysis_recipe_config.get("field_descriptions")
            or analysis_recipe_config.get("prompt_user")
        )
        _run_learning_mature = (
            _run_first_pass_had_learning
            and _run_learning_version >= 2
            and confianza >= classification_threshold
        )
        _run_rerun_allowed = bool(learning_ctrl.get("rerun_enabled", True)) and float(
            confianza or 0.0
        ) >= float(learning_ctrl.get("rerun_min_confidence", 0.0))
        if (
            auto_rc2
            and not auto_recipe_created
            and not local_recipe_config
            and not _run_learning_mature
            and _run_rerun_allowed
        ):
            baseline_routing = build_document_routing_decision(
                source_doc_type=tipo_doc,
                ai_confidence=confianza,
                extracted_data=analysis_fields if isinstance(analysis_fields, dict) else {},
                canonical_document={},
                category_keywords=get_doc_categories(db),
                requires_review=requiere_revision,
                db=db,
                tenant_id=tenant_id,
            )
            if should_run_learning_rerun(
                baseline_confidence=confianza,
                classification_threshold=classification_threshold,
                baseline_fields=analysis_fields if isinstance(analysis_fields, dict) else {},
                baseline_routing=baseline_routing,
                base_recipe_config=analysis_recipe_config,
                candidate_recipe_config=auto_rc2,
            ):
                ai_rerun_started_at = time.perf_counter()
                rerun_analysis = await analyze_document_fn(
                    llm_content,
                    filename,
                    extraction.get("format", tipo_archivo),
                    has_structured_rows=False,
                    recipe_config=auto_rc2,
                    structured_data=None,
                    structured_metadata=None,
                    image_bytes=(
                        bytes(vision_image_bytes)
                        if (is_image_doc or is_scanned_pdf) and vision_image_bytes
                        else None
                    ),
                    fallback_patterns=fallback_patterns,
                    canonical_fields=canonical_fields,
                    prompt_config=prompt_config,
                    reprocess_mode=reprocess_mode,
                    bypass_cache=deep_reprocess,
                    deep_reprocess_context=recipe_context.reprocess_context,
                    deep_focus_fields=(
                        _reprocess_context_summary(recipe_context.reprocess_context).get(
                            "missing_fields"
                        )
                        if deep_reprocess
                        else None
                    ),
                )
                _set_stage_timing(stage_timings, "ai_rerun", ai_rerun_started_at)
                rerun_normalized = _normalize_analysis_output(rerun_analysis)
                rerun_fields = rerun_normalized["fields"]
                if isinstance(rerun_fields, dict) and rerun_fields:
                    analysis = rerun_analysis
                    normalized_analysis = rerun_normalized
                    tipo_doc = str(rerun_normalized["doc_type"])
                    confianza = float(rerun_normalized["confidence"])
                    razonamiento = str(rerun_normalized["reasoning"])
                    analysis_fields = rerun_fields
                    requiere_revision = confianza < classification_threshold
                    datos_extraidos = rerun_fields
                    local_recipe_config = auto_rc2

    current_snapshot = _load_snapshot(db, local_snapshot_id)
    learning_version_applied = get_snapshot_learning_version(current_snapshot)
    postprocess_started_at = time.perf_counter()
    field_aliases = get_field_aliases(db, tenant_id=tenant_id)
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    if isinstance(datos_extraidos, dict):
        unmapped_cols = _normalize_line_item_extra_columns(datos_extraidos, field_aliases)
        _project_line_item_slots(datos_extraidos, canonical_fields)
        if unmapped_cols:
            try:
                _learn_column_candidates(
                    db,
                    col_names=unmapped_cols,
                    doc_type=tipo_doc,
                    tenant_id=tenant_id,
                    field_aliases=field_aliases,
                    canonical_fields=canonical_fields,
                )
            except Exception as exc:
                logger.debug("Column candidate learning error (non-fatal): %s", exc)
    canonical_document, projection = build_document_projection(
        datos_extraidos if isinstance(datos_extraidos, dict) else {},
        doc_type=tipo_doc,
        source_format=extraction.get("format", tipo_archivo),
        field_aliases=field_aliases,
        canonical_fields=canonical_fields,
    )
    _set_stage_timing(stage_timings, "postprocess_projection", postprocess_started_at)
    model_used = analysis.get("model_used") or "unknown"
    raw_ai_json = {
        "run": {
            "recipe_resolution": {
                "recipe_id": str(recipe_context.recipe_id) if recipe_context.recipe_id else None,
                "recipe_snapshot_id": str(local_snapshot_id) if local_snapshot_id else None,
                "used": local_resolution,
                "force": force,
                "force_clean_reimport": force_clean_reimport,
                "explicit_recipe_context": recipe_context.explicit_recipe_context,
                "learning_version_applied": learning_version_applied,
                "generated_auto_snapshot_id": (
                    str(generated_auto_snapshot_id) if generated_auto_snapshot_id else None
                ),
                "generated_auto_snapshot_mode": generated_auto_mode,
            },
            "learning_version_applied": learning_version_applied,
            "model": model_used,
            "reprocess": {
                "mode": reprocess_mode,
                "deep": deep_reprocess,
                "ocr_cache_hit": bool(extraction.get("_cache_hit")),
                "ocr_cache_bypassed": bool(extraction.get("_cache_bypassed")),
                "ai_cache_hit": bool(analysis.get("cache_hit")),
                "ai_cache_bypassed": bool(analysis.get("cache_bypassed")),
                "result_changed": reprocess_result_changed,
                "context": reprocess_context_summary,
            },
        },
        "analysis": {
            "prompt": analysis.get("prompt_sent", ""),
            "raw_response": analysis.get("raw_response", ""),
            "parsed": {
                "tipo_documento": tipo_doc,
                "confianza": confianza,
                "razonamiento": razonamiento,
                "es_tabla": has_structured,
            },
            "campos_extraidos": (
                list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
            ),
        },
        "canonical_document": canonical_document,
    }

    datos_extraidos = (
        _json_safe(datos_extraidos)
        if isinstance(datos_extraidos, (dict, list))
        else datos_extraidos
    )
    sheet_profiles = (
        _json_safe(sheet_profiles) if isinstance(sheet_profiles, (dict, list)) else sheet_profiles
    )
    raw_ai_json = _json_safe(raw_ai_json)

    document_update_started_at = time.perf_counter()
    crud.update_documento(
        db,
        doc,
        {
            "texto_ocr": text[
                : max(1, int(processing_cfg.get("persist_text_ocr_max_chars") or 50000))
            ],
            "tipo_documento_detectado": tipo_doc,
            "confianza_clasificacion": confianza,
            "requiere_revision": requiere_revision,
            "datos_extraidos": datos_extraidos,
            "estado": "REVIEW",
            **projection,
            "llm_model": model_used,
            "raw_ai_json": raw_ai_json,
            "fingerprint_json": sheet_profiles,
            "sheet_profiles_json": sheet_profiles,
            "recipe_snapshot_id": local_snapshot_id,
        },
    )
    _set_stage_timing(stage_timings, "document_update", document_update_started_at)
    raw_ai_json["run"].update(
        _build_timing_summary(stage_timings=stage_timings, started_at=processing_started_at)
    )
    crud.update_documento(db, doc, {"raw_ai_json": raw_ai_json})
    crud.add_log(
        db,
        doc.id,
        "EXTRACT",
        user_id,
        {
            "campos_extraidos": (
                list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
            ),
            "model": model_used,
            "recipe_mode": local_resolution,
            "auto_recipe_created": auto_recipe_created,
            "force_clean_reimport": force_clean_reimport,
            "reprocess_mode": reprocess_mode,
            "reprocess_cache_hit": bool(analysis.get("cache_hit")),
            "reprocess_cache_bypassed": bool(analysis.get("cache_bypassed")),
            "reprocess_result_changed": reprocess_result_changed,
            "reprocess_missing_fields": reprocess_context_summary.get("missing_fields", []),
            "generated_auto_snapshot_id": (
                str(generated_auto_snapshot_id) if generated_auto_snapshot_id else None
            ),
        },
    )
    logger.info(
        "importador.processing.completed doc_id=%s mode=%s metrics=%s",
        doc.id,
        "run",
        _json_safe(
            {
                "tenant_id": str(tenant_id),
                "doc_type": tipo_doc,
                "model": model_used,
                **raw_ai_json["run"],
            }
        ),
    )

    return DocumentProcessingResult(
        tipo_documento_detectado=tipo_doc,
        confianza_clasificacion=confianza,
        requiere_revision=requiere_revision,
        datos_extraidos=datos_extraidos if isinstance(datos_extraidos, dict) else None,
        llm_model=model_used,
        recipe_snapshot_id=local_snapshot_id,
        recipe_used=local_resolution,
        auto_recipe_created=auto_recipe_created or None,
        auto_recipe_name=auto_recipe_name,
        raw_ai_json=raw_ai_json,
    )
