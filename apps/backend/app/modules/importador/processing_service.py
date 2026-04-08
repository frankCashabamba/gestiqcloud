from __future__ import annotations

import logging
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
    load_ai_params,
    load_amount_label_config,
    load_classification_threshold,
    load_doc_type_patterns,
    load_learning_control,
    load_pdf_table_parse_config,
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
from .text_fallback_extractor import extract_fields_from_text, learn_labels_from_text
from .utils import json_safe as _json_safe

logger = logging.getLogger("importador.processing")

AnalyzeDocumentFn = Callable[..., Awaitable[dict[str, Any]]]
ExtractTextFn = Callable[[bytes, str], Awaitable[dict[str, Any]]]
ProcessingMode = Literal["upload", "run", "async"]

_AI_FAILURE_TOKENS = ("timeout", "timed out", "unavailable", "connection", "refused", "failed")


def _analysis_indicates_ai_failure(analysis: dict[str, Any]) -> bool:
    """Detect whether the AI analysis failed (timeout, connection error, etc.)."""
    combined = " ".join(
        str(analysis.get(k, "") or "") for k in ("raw_response", "reasoning", "error", "model_used")
    ).lower()
    return any(token in combined for token in _AI_FAILURE_TOKENS)


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


@dataclass(slots=True)
class RecipeContext:
    recipe_config: dict[str, Any] = field(default_factory=dict)
    resolution_mode: str = "zero_shot"
    resolved_snapshot_id: UUID | str | None = None
    explicit_recipe_context: bool = False
    force_clean_reimport: bool = False
    recipe_id: UUID | None = None


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
    vision_image_bytes: bytes | bytearray | None,
    fallback_patterns: dict[str, Any],
    canonical_fields: dict[str, Any],
    prompt_config: dict[str, Any],
    db: Any = None,
) -> dict[str, Any]:
    # Si el OCR ya extrajo texto suficiente, no usar visión.
    # La visión solo aplica a imágenes puras o PDFs sin texto extraíble.
    text_is_sufficient = bool(content and len(content.strip()) >= 100)
    image_bytes = (
        None if text_is_sufficient else bytes(vision_image_bytes) if vision_image_bytes else None
    )
    return await analyze_document_fn(
        content,
        filename,
        format_hint,
        has_structured_rows=has_structured_rows,
        recipe_config=recipe_config,
        image_bytes=image_bytes,
        fallback_patterns=fallback_patterns,
        canonical_fields=canonical_fields,
        prompt_config=prompt_config,
        db=db,
    )


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
    return await _process_upload_like_document(
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


async def _process_upload_like_document(
    *,
    mode: Literal["upload", "async"],
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
    extraction = await extract_text_fn(file_bytes, filename)
    text = extraction.get("text", "")
    structured = extraction.get("structured_data")
    sheet_profiles = extraction.get("sheet_profiles")

    has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)

    headers_norm: list[str] = []
    headers_display: list[str] = []
    if has_structured:
        for profile in sheet_profiles.values():
            headers_norm = profile.get("headers_norm") or []
            headers_display = profile.get("headers") or headers_norm
            break

    resolved_snapshot_id = recipe_context.resolved_snapshot_id
    resolution_mode = recipe_context.resolution_mode or "zero_shot"
    explicit_recipe_context = recipe_context.explicit_recipe_context
    if not resolved_snapshot_id and not recipe_context.force_clean_reimport:
        existing_snapshot_id = getattr(doc, "recipe_snapshot_id", None)
        if existing_snapshot_id:
            resolved_snapshot_id = existing_snapshot_id
            explicit_recipe_context = True
            if resolution_mode == "zero_shot":
                resolution_mode = "snapshot"
    if sheet_profiles:
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
        sample_lines = [f"Columnas: {headers_display}"]
        for row in structured[:5] if isinstance(structured, list) else []:
            if isinstance(row, dict):
                sample_lines.append(
                    str({k: v for k, v in list(row.items())[:8] if not k.startswith("_")})
                )
        llm_content = "\n".join(sample_lines)
    else:
        llm_content = text[:6000] if text else ""

    vision_image_bytes = extraction.get("vision_image_bytes")
    if not isinstance(vision_image_bytes, (bytes, bytearray)):
        vision_image_bytes = file_bytes if tipo_archivo in ("JPG", "PNG", "IMG") else None

    recipe_snapshot = None
    recipe_config: dict[str, Any] = {}
    cached_analysis = None
    text_cached_analysis = None
    analysis_recipe_config: dict[str, Any] = {}
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

    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    prompt_config = load_prompt_config(db)
    fallback_patterns = load_doc_type_patterns(db)
    classification_threshold = load_classification_threshold(db)
    learning_ctrl = load_learning_control(db)

    # ── Pre-classification: attempt to resolve doc_type without AI ──────────────
    _field_aliases_for_pre = get_field_aliases(db, tenant_id=tenant_id)
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

    if pre_class and pre_class.skip_ai:
        if pre_class.layer == "template":
            # L5: Template extraction — campos extraídos directamente, sin AI
            analysis = {
                **(pre_class.cached_analysis or {}),
                "model_used": f"pre-classifier/template",
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
        _TABLE_ONLY_TYPES = {
            "INVENTORY",
            "PRICE_LIST",
            "COSTING",
            "PAYROLL",
            "BANK_STATEMENT",
            "BANK_MOVEMENTS",
            "PRODUCT_LIST",
        }
        _rc_for_ai = dict(recipe_config) if recipe_config else {}
        if pre_class and pre_class.confidence >= 0.65:
            _hint_type = pre_class.doc_type.upper()
            if has_structured or _hint_type not in _TABLE_ONLY_TYPES:
                _rc_for_ai["doc_type_hint"] = pre_class.doc_type
                _rc_for_ai["doc_type_hint_confidence"] = pre_class.confidence
        if not has_structured and text_cached_analysis and not _rc_for_ai.get("doc_type_hint"):
            _cached_type = str(text_cached_analysis.get("doc_type") or "").upper()
            _cached_conf = float(text_cached_analysis.get("confidence") or 0)
            if _cached_type and _cached_type != "OTHER" and _cached_conf >= 0.65:
                if _cached_type not in _TABLE_ONLY_TYPES:
                    _rc_for_ai["doc_type_hint"] = _cached_type
                    _rc_for_ai["doc_type_hint_confidence"] = _cached_conf
        analysis_recipe_config = dict(_rc_for_ai)
        analysis = await _analyze_with_context(
            analyze_document_fn=analyze_document_fn,
            content=llm_content,
            filename=filename,
            format_hint=extraction.get("format", tipo_archivo),
            has_structured_rows=has_structured,
            recipe_config=_rc_for_ai,
            vision_image_bytes=vision_image_bytes,
            fallback_patterns=fallback_patterns,
            canonical_fields=canonical_fields,
            prompt_config=prompt_config,
            db=db,
        )

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

    normalized_analysis = _normalize_analysis_output(analysis)
    tipo_doc = str(normalized_analysis["doc_type"])
    confianza = float(normalized_analysis["confidence"])
    requiere_revision = confianza < classification_threshold
    razonamiento = str(normalized_analysis["reasoning"])
    analysis_fields = normalized_analysis["fields"]

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
        sheet_used = extraction.get("sheet_used")
        sheet_metadata = extraction.get("sheet_metadata") or {}
        filas_por_hoja: dict[str, list] = {}
        for row in structured or []:
            if isinstance(row, dict):
                sheet_name = str(row.get("_sheet") or sheet_used or "")
                if sheet_name:
                    filas_por_hoja.setdefault(sheet_name, []).append(row)
        datos_extraidos = {
            "filas": structured[:200],
            "total_filas": len(structured),
            "columnas": headers_display or headers_norm,
            "columnas_norm": headers_norm,
            "filas_por_hoja": filas_por_hoja,
            "metadata_por_hoja": sheet_metadata,
            "sheet_usada": sheet_used,
        }
        if looks_like_product_document(
            datos_extraidos,
            sheet_name=sheet_used,
            detection_config=load_product_sheet_detection_config(db),
        ) and tipo_doc not in {"INVENTORY", "PRICE_LIST", "PRODUCT_LIST", "PRODUCTS"}:
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
        if not datos_extraidos and text.strip() and _analysis_indicates_ai_failure(analysis):
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
            )
            if fallback_fields:
                datos_extraidos = fallback_fields
                requiere_revision = True
                _used_text_fallback = True

        if tipo_doc != "OTHER" and not explicit_recipe_context:
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
            _rerun_allowed = (
                bool(learning_ctrl.get("rerun_enabled", True))
                and float(confianza or 0.0) >= float(learning_ctrl.get("rerun_min_confidence", 0.0))
            )
            if auto_recipe_config and not auto_recipe_created and not _learning_mature and _rerun_allowed:
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
                    rerun_analysis = await _analyze_with_context(
                        analyze_document_fn=analyze_document_fn,
                        content=llm_content,
                        filename=filename,
                        format_hint=extraction.get("format", tipo_archivo),
                        has_structured_rows=False,
                        recipe_config=rerun_recipe_config,
                        vision_image_bytes=vision_image_bytes,
                        fallback_patterns=fallback_patterns,
                        canonical_fields=canonical_fields,
                        prompt_config=prompt_config,
                        db=db,
                    )
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
            )
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

    crud.update_documento(
        db,
        doc,
        {
            "texto_ocr": text[:50000],
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

    if isinstance(datos_extraidos, dict):
        upsert_staging_lines_from_extraction(db, doc.id, tenant_id, datos_extraidos)

    review_hints = _build_review_hints(
        db,
        doc=doc,
        routing_decision=routing_decision,
        snapshot_id=resolved_snapshot_id,
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
    extraction = await extract_text_fn(file_bytes, filename)
    text = extraction.get("text", "")
    structured = extraction.get("structured_data")
    sheet_profiles = extraction.get("sheet_profiles")
    sheet_metadata = extraction.get("sheet_metadata") or {}
    sheet_used = extraction.get("sheet_used")

    has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)
    structured_rows_all: list[dict[str, Any]] = structured if isinstance(structured, list) else []
    structured_rows: list[dict[str, Any]] = list(structured_rows_all)

    headers_norm: list[str] = []
    headers_display: list[str] = []
    if has_structured:
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

    local_recipe_config = dict(recipe_context.recipe_config or {})
    local_resolution = (
        "force_clean"
        if recipe_context.force_clean_reimport and not local_recipe_config
        else recipe_context.resolution_mode
    )
    local_snapshot_id = (
        None
        if recipe_context.force_clean_reimport and not local_recipe_config
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
    if sheet_profiles and not local_recipe_config:
        auto_rc, auto_snap_id, auto_mode, local_auto_created, local_auto_name = resolve_auto_recipe(
            db, tenant_id, sheet_profiles, user_id, force_new=force
        )
        generated_auto_snapshot_id = auto_snap_id
        generated_auto_mode = auto_mode
        if recipe_context.force_clean_reimport:
            local_recipe_config = {}
            local_resolution = "force_clean"
            local_snapshot_id = None
        else:
            if auto_rc:
                local_recipe_config = auto_rc
                local_resolution = auto_mode
            if auto_snap_id:
                local_snapshot_id = auto_snap_id

    recipe_name_detected: str | None = None
    if has_structured:
        sheet_names = list(sheet_profiles.keys()) if sheet_profiles else []
        if sheet_used is None and sheet_names:
            sheet_used = sheet_names[0]
        sample_lines = [f"Columnas: {headers_display}"]
        for row in structured_rows[:5]:
            if isinstance(row, dict):
                sample_lines.append(
                    str({k: v for k, v in list(row.items())[:8] if not k.startswith("_")})
                )
                if recipe_name_detected is None:
                    for key in row.keys():
                        key_norm = str(key or "").strip().lower()
                        if key_norm in (
                            "nombre_de_la_receta",
                            "nombre_receta",
                            "nombre de la receta",
                            "nombre",
                        ):
                            value = row.get(key)
                            if value:
                                recipe_name_detected = str(value).strip()
                                break
        llm_content = "\n".join(sample_lines)
    else:
        llm_content = text[:6000] if text else ""

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

    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    prompt_config = load_prompt_config(db)
    fallback_patterns = load_doc_type_patterns(db)
    classification_threshold = load_classification_threshold(db)
    learning_ctrl = load_learning_control(db)
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
        if text_cached_analysis_run and not _rc_for_run.get("doc_type_hint"):
            _cached_type = str(text_cached_analysis_run.get("doc_type") or "").upper()
            _cached_conf = float(text_cached_analysis_run.get("confidence") or 0)
            if _cached_type and _cached_type != "OTHER" and _cached_conf >= 0.65:
                _rc_for_run["doc_type_hint"] = _cached_type
                _rc_for_run["doc_type_hint_confidence"] = _cached_conf
        analysis = await analyze_document_fn(
            llm_content,
            filename,
            extraction.get("format", tipo_archivo),
            has_structured_rows=has_structured,
            recipe_config=_rc_for_run,
            image_bytes=(
                bytes(vision_image_bytes)
                if (is_image_doc or is_scanned_pdf) and vision_image_bytes
                else None
            ),
            fallback_patterns=fallback_patterns,
            canonical_fields=canonical_fields,
            prompt_config=prompt_config,
        )
    normalized_analysis = _normalize_analysis_output(analysis)

    tipo_doc = str(normalized_analysis["doc_type"])
    confianza = float(normalized_analysis["confidence"])
    razonamiento = str(normalized_analysis["reasoning"])
    analysis_fields = normalized_analysis["fields"]
    requiere_revision = confianza < classification_threshold

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
            for row in structured_rows[:200]:
                if not isinstance(row, dict):
                    continue
                for key in row.keys():
                    key_norm = str(key or "").strip().lower()
                    if key_norm in (
                        "nombre_de_la_receta",
                        "nombre_receta",
                        "nombre de la receta",
                        "nombre",
                    ):
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
                if (
                    key_norm
                    in (
                        "nombre_de_la_receta",
                        "nombre_receta",
                        "nombre de la receta",
                        "nombre",
                    )
                    and value
                ):
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
            "filas": structured_rows[:200],
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
                key: value[:200] for key, value in filas_por_hoja.items()
            }
            datos_extraidos["filas_por_hoja_count"] = filas_count
        if looks_like_product_document(
            datos_extraidos,
            sheet_name=sheet_used,
            detection_config=load_product_sheet_detection_config(db),
        ) and tipo_doc not in {"INVENTORY", "PRICE_LIST", "PRODUCT_LIST", "PRODUCTS"}:
            tipo_doc = "INVENTORY"
            requiere_revision = True
    else:
        datos_extraidos = analysis_fields or {}

    auto_recipe_created = local_auto_created
    auto_recipe_name: str | None = local_auto_name
    if not sheet_profiles and tipo_doc != "OTHER" and not recipe_context.explicit_recipe_context:
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
        _run_rerun_allowed = (
            bool(learning_ctrl.get("rerun_enabled", True))
            and float(confianza or 0.0) >= float(learning_ctrl.get("rerun_min_confidence", 0.0))
        )
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
                rerun_analysis = await analyze_document_fn(
                    llm_content,
                    filename,
                    extraction.get("format", tipo_archivo),
                    has_structured_rows=False,
                    recipe_config=auto_rc2,
                    image_bytes=(
                        bytes(vision_image_bytes)
                        if (is_image_doc or is_scanned_pdf) and vision_image_bytes
                        else None
                    ),
                    fallback_patterns=fallback_patterns,
                    canonical_fields=canonical_fields,
                    prompt_config=prompt_config,
                )
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
    model_used = analysis.get("model_used") or "unknown"
    raw_ai_json = {
        "run": {
            "recipe_resolution": {
                "recipe_id": str(recipe_context.recipe_id) if recipe_context.recipe_id else None,
                "recipe_snapshot_id": str(local_snapshot_id) if local_snapshot_id else None,
                "used": local_resolution,
                "force": force,
                "force_clean_reimport": recipe_context.force_clean_reimport,
                "explicit_recipe_context": recipe_context.explicit_recipe_context,
                "learning_version_applied": learning_version_applied,
                "generated_auto_snapshot_id": (
                    str(generated_auto_snapshot_id) if generated_auto_snapshot_id else None
                ),
                "generated_auto_snapshot_mode": generated_auto_mode,
            },
            "learning_version_applied": learning_version_applied,
            "model": model_used,
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

    crud.update_documento(
        db,
        doc,
        {
            "texto_ocr": text[:50000],
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
            "force_clean_reimport": recipe_context.force_clean_reimport,
            "generated_auto_snapshot_id": (
                str(generated_auto_snapshot_id) if generated_auto_snapshot_id else None
            ),
        },
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
