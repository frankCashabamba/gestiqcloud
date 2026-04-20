from __future__ import annotations

import logging
import re
import time
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from . import crud, recipe_crud
from .ai_classifier import _apply_high_evidence_ocr_repairs, _normalize_invoice_description_strict
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
from .doc_type_resolution import promote_doc_type_from_text_fallback
from .document_fields import safe_floatish
from .field_alias_loader import get_canonical_fields, get_field_aliases
from .invoice_ocr_rescue import invoice_rescue_from_ocr
from .ocr_quality import estimate_text_quality as _estimate_text_quality
from .product_import_service import looks_like_product_document
from .runtime_config import (
    load_amount_label_config,
    load_classification_threshold,
    load_doc_type_patterns,
    load_doc_type_resolution_config,
    load_learning_control,
    load_ocr_runtime_config,
    load_pdf_table_parse_config,
    load_processing_config,
    load_processing_runtime_config,
    load_product_sheet_detection_config,
    load_prompt_config,
    load_structured_filename_patterns,
)
from .schemas import DocumentReviewHintOut, DocumentRoutingDecision
from .services.document_model_learning_service import should_run_learning_rerun
from .services.document_routing_agent import build_document_routing_decision
from .snapshot_learning import build_snapshot_review_hints
from .text_fallback_extractor import extract_fields_from_text
from .utils import json_safe as _json_safe

logger = logging.getLogger("importador.processing")

AnalyzeDocumentFn = Callable[..., Awaitable[dict[str, Any]]]
ExtractTextFn = Callable[..., Awaitable[dict[str, Any]]]

# Estrategias de procesamiento y sus timeouts por defecto.
# Los timeouts de la BD (imp_config) tienen prioridad si están configurados.
_STRATEGY_TIMEOUTS: dict[str, float] = {
    "structured_fast": 10.0,
    "text_doc": 15.0,
    "visual_complex": 25.0,
}

# Formatos con parser determinista propio: no necesitan LLM si ya hay estructura utilizable.
# La clasificación (doc_type) se toma del recipe hint o se deja como "STRUCTURED".
_STRUCTURED_SKIP_FORMATS: frozenset[str] = frozenset(
    {
        "CSV",
        "XML",
        "XML_FACTURAE",
        "XML_UBL",
        "JSON",
        "XLS",
        "XLSX",
        "EXCEL",
    }
)

# Formatos XML de facturas electrónicas con parser determinista: el tipo de documento
# y los campos clave se leen directamente del header estructurado, sin necesidad de LLM.
_XML_INVOICE_FORMATS: frozenset[str] = frozenset({"XML_FACTURAE", "XML_UBL"})

# Mapa de tipo_documento (según parser XML) → doc_type canónico del sistema.
_XML_TIPO_DOCUMENTO_MAP: dict[str, str] = {
    "FACTURA": "INVOICE",
    "NOTA_CREDITO": "CREDIT_NOTE",
    "NOTA_DEBITO": "DEBIT_NOTE",
    "RECIBO": "RECEIPT",
    "BOLETA": "RECEIPT",
}

# Mapa de clave del header XML → nombre de campo canónico del sistema.
_XML_HEADER_TO_CANONICAL: dict[str, str] = {
    "fecha": "issue_date",
    "monto": "total_amount",
    "subtotal": "subtotal",
    "igv": "tax_amount",
    "impuesto": "tax_amount",
    "proveedor": "vendor",
    "comprador": "buyer",
    "documento": "doc_number",
    "ruc": "vendor_tax_id",
    "moneda": "currency",
}

# Formatos puramente visuales: suelen entrar por deep; si el OCR ya es suficiente,
# se prefieren texto-primero y la visión queda como rescate.
# PDF_OCR se excluye aquí: tiene texto OCR y se enruta por calidad (bloque pdf_ocr en decide_processing_lane).
_VISUAL_FORMATS: frozenset[str] = frozenset(
    {
        "JPG",
        "JPEG",
        "PNG",
        "IMG",
        "HEIC",
        "WEBP",
        "IMAGE_OCR",
    }
)

# Timeouts por carril (segundos). Los valores de imp_config tienen prioridad.
# deep=90s → cada fase (texto/visión) dispone de 45s; aumentado desde 40s porque
# PDFs complejos y modelos locales grandes necesitan más margen para no caer en fallback.
_LANE_TIMEOUTS: dict[str, float] = {
    "fast": 12.0,
    "deep": 90.0,
}


def _resolve_processing_config(db: Any | None = None) -> dict[str, Any]:
    """Load the runtime processing config, swallowing any backend error.

    The hardcoded constants above act as the safe fallback so callers that
    cannot reach the runtime store keep working with the same behaviour.
    """
    try:
        return load_processing_config(db)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("processing runtime config unavailable: %s", exc)
        return {}


def _get_strategy_timeouts(db: Any | None = None) -> dict[str, float]:
    cfg = _resolve_processing_config(db)
    return {
        "structured_fast": float(
            cfg.get("strategy_timeout_structured_fast") or _STRATEGY_TIMEOUTS["structured_fast"]
        ),
        "text_doc": float(cfg.get("strategy_timeout_text_doc") or _STRATEGY_TIMEOUTS["text_doc"]),
        "visual_complex": float(
            cfg.get("strategy_timeout_visual_complex") or _STRATEGY_TIMEOUTS["visual_complex"]
        ),
    }


def _get_lane_timeouts(db: Any | None = None) -> dict[str, float]:
    cfg = _resolve_processing_config(db)
    return {
        "fast": float(cfg.get("lane_timeout_fast") or _LANE_TIMEOUTS["fast"]),
        "deep": float(cfg.get("lane_timeout_deep") or _LANE_TIMEOUTS["deep"]),
    }


def _get_structured_skip_formats(db: Any | None = None) -> frozenset[str]:
    cfg = _resolve_processing_config(db)
    formats = cfg.get("structured_skip_formats")
    if isinstance(formats, (frozenset, set)) and formats:
        return frozenset(str(item).strip().upper() for item in formats if str(item).strip())
    if isinstance(formats, list) and formats:
        return frozenset(str(item).strip().upper() for item in formats if str(item).strip())
    return _STRUCTURED_SKIP_FORMATS


def _get_xml_invoice_formats(db: Any | None = None) -> frozenset[str]:
    cfg = _resolve_processing_config(db)
    formats = cfg.get("xml_invoice_formats")
    if isinstance(formats, (frozenset, set)) and formats:
        return frozenset(str(item).strip().upper() for item in formats if str(item).strip())
    if isinstance(formats, list) and formats:
        return frozenset(str(item).strip().upper() for item in formats if str(item).strip())
    return _XML_INVOICE_FORMATS


def _get_visual_formats(db: Any | None = None) -> frozenset[str]:
    cfg = _resolve_processing_config(db)
    formats = cfg.get("visual_formats")
    if isinstance(formats, (frozenset, set)) and formats:
        return frozenset(str(item).strip().upper() for item in formats if str(item).strip())
    if isinstance(formats, list) and formats:
        return frozenset(str(item).strip().upper() for item in formats if str(item).strip())
    return _VISUAL_FORMATS


def decide_processing_strategy(
    *,
    tipo_archivo: str,
    has_vision: bool,
    text_len: int,
    has_structured_rows: bool,
    processing_cfg: dict[str, Any] | None = None,
) -> tuple[str, float, bool]:
    """Decide la estrategia de procesamiento según el tipo y complejidad del documento.

    Returns:
        (strategy_name, timeout_secs, force_vision)
        - strategy_name: "structured_fast" | "text_doc" | "visual_complex"
        - timeout_secs:  timeout a usar para la llamada AI (anula el default del proveedor)
        - force_vision:  True si se debe intentar el modelo de visión aunque el OCR sea bueno
    """
    cfg = processing_cfg or {}
    tipo = str(tipo_archivo or "").upper()

    # Timeouts configurables desde BD (imp_config), con fallback a los defaults
    t_fast = float(
        cfg.get("strategy_timeout_structured_fast") or _STRATEGY_TIMEOUTS["structured_fast"]
    )
    t_text = float(cfg.get("strategy_timeout_text_doc") or _STRATEGY_TIMEOUTS["text_doc"])
    t_visual = float(
        cfg.get("strategy_timeout_visual_complex") or _STRATEGY_TIMEOUTS["visual_complex"]
    )

    # 1. Documentos estructurados: nunca necesitan LLM pesado
    if has_structured_rows or tipo in {"XLSX", "XLS", "CSV", "XML", "JSON"}:
        return "structured_fast", t_fast, False

    # 2. Imágenes o PDFs escaneados: siempre paciente + intentar visión
    image_types = {"JPG", "JPEG", "PNG", "IMG", "HEIC", "WEBP", "IMAGE_OCR"}
    if has_vision or tipo in image_types:
        return "visual_complex", t_visual, True

    # 3. PDFs con texto claro: timeout moderado, sin visión forzada
    if text_len >= 800:
        return "text_doc", t_text, False

    # 4. PDF con texto escaso: más tiempo, sin visión
    return "visual_complex", t_visual, False


@dataclass(slots=True)
class LaneDecision:
    """Resultado de la decisión de carril para un documento."""

    lane: str  # "fast" | "deep"
    timeout_secs: float  # timeout por fase LLM (mitad del budget total para deep con 2 fases)
    force_vision: bool
    vision_first: bool  # deep only: True=visión antes de texto, False=texto antes de visión
    reasons: list[str]


def decide_processing_lane(
    *,
    doc_format: str,
    has_structured: bool,
    has_vision: bool,
    text_is_sufficient: bool,
    has_semantic_hint: bool,
    has_cached_analysis: bool,
    is_first_import: bool,
    previous_confidence: float | None,
    deep_reprocess: bool,
    processing_cfg: dict[str, Any],
    ocr_quality_score: float | None = None,
) -> LaneDecision:
    """Decide el carril de procesamiento (fast/deep) usando señales post-OCR.

    Fast lane  → latencia baja.  Documentos estructurados (bypass directo sin LLM)
                  o reimportaciones de texto con alta confianza previa.
    Deep lane  → exactitud máxima.  Docs visuales, escaneados, primera importación
                  ambigua, baja calidad OCR o confianza previa insuficiente.

    Timeouts provienen de imp_config (lane_timeout_fast / lane_timeout_deep);
    si no están configurados se usan los defaults de _LANE_TIMEOUTS.

    Para deep lane con documentos de texto+imagen, `timeout_secs` es el presupuesto
    por fase (no el total). El total máximo es 2 × timeout_secs = t_deep.

    vision_first determina el orden de fases en deep lane:
      True  → OCR malo / doc visual: visión primero; si acierta, texto no se ejecuta.
      False → OCR decente: texto primero; si acierta, visión no se ejecuta.

    Nota: documentos estructurados con `has_structured=True` llaman siempre a
    _structured_direct_analysis (bypass local, sin HTTP al proveedor LLM). Por eso
    son candidatos naturales a fast lane independientemente de is_first_import.
    """
    fmt = str(doc_format or "").upper()

    t_fast = float(processing_cfg.get("lane_timeout_fast") or _LANE_TIMEOUTS["fast"])
    t_deep = float(processing_cfg.get("lane_timeout_deep") or _LANE_TIMEOUTS["deep"])
    # Por fase en deep: mitad del presupuesto total para dejar margen a ambas fases.
    t_deep_phase = t_deep / 2.0

    # Umbral de calidad OCR a partir del cual se prefiere texto-primero en deep.
    _ocr_quality_threshold = float(processing_cfg.get("ocr_quality_vision_threshold") or 0.45)

    def _vision_first_from_quality() -> bool:
        """True si la calidad OCR es insuficiente (visión rinde más)."""
        if ocr_quality_score is None:
            return True  # sin datos → conservador → visión primero
        return ocr_quality_score < _ocr_quality_threshold

    # ── Deep incondicional ─────────────────────────────────────────────────
    if deep_reprocess:
        _vf = _vision_first_from_quality()
        return LaneDecision("deep", t_deep_phase, False, _vf, ["deep_reprocess_mode"])

    visual_formats = processing_cfg.get("visual_formats")
    if not isinstance(visual_formats, (frozenset, set)) or not visual_formats:
        visual_formats = _get_visual_formats(None)
    if has_vision or fmt in visual_formats:
        if text_is_sufficient:
            return LaneDecision(
                "deep", t_deep_phase, False, False, ["visual_or_scan_doc", "text_first"]
            )
        return LaneDecision("deep", t_deep, True, True, ["visual_or_scan_doc", "vision_first"])

    if fmt == "PDF_OCR":
        # PDF escaneado: deep siempre, pero visión-primero solo si OCR es muy malo.
        # Umbral bajo (0.25) para ser conservadores: solo los peores PDFs van vision-first.
        # PDFs con OCR aceptable (score >= 0.25) usan texto-primero y visión como rescate.
        _pdf_vision_threshold = float(
            processing_cfg.get("ocr_pdf_vision_primary_threshold") or 0.25
        )
        _ocr_very_bad = ocr_quality_score is None or ocr_quality_score < _pdf_vision_threshold
        _pdf_reasons = ["pdf_ocr_scanned"]
        if ocr_quality_score is not None:
            _pdf_reasons.append(f"ocr_quality={ocr_quality_score:.2f}")
        _pdf_reasons.append("vision_first" if _ocr_very_bad else "text_first")
        return LaneDecision("deep", t_deep_phase, _ocr_very_bad, _ocr_very_bad, _pdf_reasons)

    if not has_structured and not text_is_sufficient:
        # Sin texto extraíble y sin estructura parseable: nada que hacer en fast
        _vf = _vision_first_from_quality()
        return LaneDecision("deep", t_deep_phase, False, _vf, ["no_usable_content"])

    # ── Fast: sin llamada HTTP al LLM ──────────────────────────────────────
    if has_cached_analysis:
        return LaneDecision("fast", t_fast, False, False, ["snapshot_cache_hit"])

    if has_structured:
        # _structured_direct_analysis hace bypass local; el timeout es irrelevante.
        if has_semantic_hint:
            return LaneDecision("fast", t_fast, False, False, ["structured_with_hint"])
        return LaneDecision("fast", t_fast, False, False, ["structured_direct_bypass"])

    # ── Fast: reimportación de texto con buena historia ────────────────────
    if (
        not is_first_import
        and previous_confidence is not None
        and previous_confidence >= 0.75
        and text_is_sufficient
    ):
        return LaneDecision("fast", t_fast, False, False, ["text_reimport_high_confidence"])

    # ── CSV/XML/JSON textuales: fast lane sin deep aunque no haya estructura completa
    if fmt in {"CSV", "JSON", "XML", "XML_UBL", "XML_FACTURAE"} and text_is_sufficient:
        reasons = ["parser_text_fast"]
        if has_semantic_hint:
            reasons.append("has_semantic_hint")
        return LaneDecision("fast", t_fast, False, False, reasons)

    # ── Deep por defecto: primera importación ambigua, texto insuficiente, etc.
    # Si no hay visión disponible (formato PDF con texto, sin bytes de imagen), el
    # presupuesto de la segunda fase nunca se usará: darle el presupuesto completo
    # al modelo de texto en lugar de reservar la mitad para una visión que no existe.
    _vf = _vision_first_from_quality()
    reasons = ["default_deep"]
    if ocr_quality_score is not None:
        reasons.append(f"ocr_quality={ocr_quality_score:.2f}")
    _phase_budget = t_deep if not has_vision else t_deep_phase
    if not has_vision:
        reasons.append("full_budget_no_vision")
    return LaneDecision("deep", _phase_budget, False, _vf, reasons)


# Tipos documentales "fuertes" que requieren evidencia mínima para ser aceptados tras fallback.
_FALLBACK_STRONG_TYPES: frozenset[str] = frozenset(
    {
        "INVOICE",
        "RECEIPT",
        "PAYROLL",
        "CREDIT_NOTE",
        "DEBIT_NOTE",
    }
)
# Campos de evidencia genéricos para tipos no-INVOICE (RECEIPT, PAYROLL, etc.).
_GENERIC_EVIDENCE_FIELDS: tuple[str, ...] = (
    "vendor",
    "doc_number",
    "total_amount",
    "subtotal",
    "issue_date",
    "line_items",
)


# ── Cambio 4: helpers de saneamiento de evidencia ─────────────────────────────


def _vendor_is_valid_evidence(vendor_value: Any) -> bool:
    """Vendor válido como evidencia: parece razón social, no narrativa ni frase larga.

    Rechaza strings que superen 120 chars o 10 palabras — señales de texto descriptivo
    que OCR confundió con un nombre de proveedor.
    """
    if not vendor_value or not isinstance(vendor_value, str):
        return False
    v = vendor_value.strip()
    if not v:
        return False
    if len(v) > 120:
        logger.info("pdf_vendor_rejected reason=narrative_text length=%d", len(v))
        return False
    if len(v.split()) > 10:
        logger.info("pdf_vendor_rejected reason=narrative_text words=%d", len(v.split()))
        return False
    return True


def _line_items_are_valid_evidence(line_items_value: Any) -> bool:
    """Line items válidos: lista no vacía donde cada item tiene al menos un campo semántico coherente.

    Rechaza tablas corruptas donde todas las filas carecen de descripción Y de campos numéricos,
    lo que indica que las columnas están cruzadas o el parser falló.
    """
    if not isinstance(line_items_value, list) or not line_items_value:
        return False
    coherent = 0
    for item in line_items_value[:5]:
        if not isinstance(item, dict):
            continue
        has_desc = bool(
            item.get("description")
            or item.get("descripcion")
            or item.get("name")
            or item.get("nombre")
        )
        has_numeric = any(
            item.get(k) is not None
            for k in (
                "quantity",
                "cantidad",
                "unit_price",
                "precio_unitario",
                "total",
                "total_price",
                "precio_total",
            )
        )
        if has_desc or has_numeric:
            coherent += 1
    if coherent == 0:
        logger.info(
            "pdf_line_items_rejected reason=incoherent_columns items_checked=%d",
            len(line_items_value[:5]),
        )
        return False
    return True


# ── Cambio 3: guard con evidencia fuerte para INVOICE ─────────────────────────


def _guard_fallback_doc_type(analysis: dict[str, Any], *, content: str = "") -> dict[str, Any]:
    """Bloquea promoción fuerte de doc_type cuando el camino final fue fallback/fallback_error.

    INVOICE requiere una combinación fuerte de campos (no basta con contar 2 campos
    cualesquiera). El vendor y los line_items se sanean antes de contar como evidencia.

    Para otros tipos fuertes (RECEIPT, PAYROLL, etc.) se mantiene el check de 2 campos.
    """
    path = str(analysis.get("analysis_path") or "").strip().lower()
    if path not in {"fallback", "fallback_error"}:
        return analysis

    doc_type = str(analysis.get("doc_type") or "OTHER").upper()
    if doc_type not in _FALLBACK_STRONG_TYPES:
        return analysis

    fields = analysis.get("fields") or {}
    if not isinstance(fields, dict):
        fields = {}

    def _has(f: str) -> bool:
        return fields.get(f) not in (None, "", [], {})

    if doc_type == "INVOICE":
        # Cambio 3: para INVOICE, exigir una combinación fuerte de evidencia.
        # Cambio 4: sanear vendor y line_items antes de contar como evidencia.
        has_total = _has("total_amount")
        has_doc_number = _has("doc_number")
        has_vendor_tax = _has("vendor_tax_id")
        has_vendor = _has("vendor") and _vendor_is_valid_evidence(fields.get("vendor"))
        has_issue_date = _has("issue_date")
        has_line_items = _line_items_are_valid_evidence(fields.get("line_items"))

        # Al menos una de estas combinaciones debe cumplirse:
        strong_evidence = (
            (has_doc_number and has_total)
            or (has_vendor_tax and has_total)
            or (has_vendor and has_total and has_issue_date)
            or (has_line_items and has_total)
        )

        if strong_evidence:
            logger.info(
                "fallback_doc_type_accepted candidate=INVOICE "
                "doc_number=%s vendor_tax=%s vendor=%s issue_date=%s line_items=%s total=%s path=%s",
                has_doc_number,
                has_vendor_tax,
                has_vendor,
                has_issue_date,
                has_line_items,
                has_total,
                path,
            )
            return analysis

        logger.info(
            "fallback_doc_type_promotion_blocked candidate=INVOICE "
            "reason=missing_strong_invoice_evidence "
            "doc_number=%s vendor_tax=%s vendor=%s issue_date=%s line_items=%s total=%s path=%s",
            has_doc_number,
            has_vendor_tax,
            has_vendor,
            has_issue_date,
            has_line_items,
            has_total,
            path,
        )
        degraded = {**analysis}
        degraded["doc_type"] = "OTHER"
        degraded["confidence"] = min(float(analysis.get("confidence") or 0.2), 0.3)
        degraded["reasoning"] = (
            f"Degraded from INVOICE to OTHER: fallback path, no strong invoice evidence combo. "
            f"Original: {analysis.get('reasoning', '')}"
        )
        logger.info(
            "fallback_doc_type_degraded from=INVOICE to=OTHER "
            "reason=missing_strong_invoice_evidence",
        )
        return degraded

    # Para RECEIPT, PAYROLL, CREDIT_NOTE, DEBIT_NOTE: mantener check de 2 campos genéricos.
    present = sum(1 for f in _GENERIC_EVIDENCE_FIELDS if fields.get(f) not in (None, "", [], {}))

    if present >= 2:
        logger.info(
            "fallback_doc_type_accepted candidate=%s fields_present=%d path=%s",
            doc_type,
            present,
            path,
        )
        return analysis

    logger.info(
        "fallback_doc_type_promotion_blocked candidate=%s reason=missing_minimum_evidence "
        "fields_present=%d required=2 path=%s",
        doc_type,
        present,
        path,
    )
    degraded = {**analysis}
    degraded["doc_type"] = "OTHER"
    degraded["confidence"] = min(float(analysis.get("confidence") or 0.2), 0.3)
    degraded["reasoning"] = (
        f"Degraded from {doc_type} to OTHER: fallback path with insufficient evidence "
        f"({present}/2 minimum evidence fields present). Original: {analysis.get('reasoning', '')}"
    )
    logger.info(
        "fallback_doc_type_degraded from=%s to=OTHER reason=insufficient_evidence_after_timeout "
        "fields_present=%d",
        doc_type,
        present,
    )
    return degraded


def _fast_lane_result_is_sufficient(
    *,
    analysis_path: str,
    tipo_doc: str,
    confianza: float,
    classification_threshold: float,
) -> tuple[bool, str]:
    """¿El resultado de fast lane es suficiente o se debe escalar a deep?

    Los caminos bypass/cache siempre son suficientes (no hubo LLM, no hay nada
    que mejorar reintentando con más tiempo).
    Solo evalúa cuando fast lane hizo una llamada LLM real (texto/PDF).

    Returns: (is_sufficient, reason_if_not)
    """
    # Bypass/cache: no hubo LLM → aceptar siempre
    if analysis_path in (
        "ok_structured",
        "ok_snapshot_cache",
        "structured_direct",
        "ok_pre_extract",
    ):
        return True, ""

    # Fallback = LLM falló (timeout, JSON inválido, excepción)
    if analysis_path in ("fallback", "fallback_error"):
        return False, "ai_fallback"

    # Tipo genérico + baja confianza = clasificación inconclusa
    if tipo_doc in ("OTHER", "STRUCTURED") and confianza < classification_threshold:
        return False, f"generic_low_confidence_type_{tipo_doc}"

    return True, ""


def _pre_extract_route_decision(
    *,
    pre_fields: dict[str, Any],
    processing_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether deterministic extraction is strong enough to skip the LLM.

    The decision is intentionally explicit and configurable so the import flow can
    skip AI only when native parsers already produced enough signal.
    """
    total_amount = safe_floatish(pre_fields.get("total_amount"))
    has_total = total_amount is not None and abs(float(total_amount)) > 0.0
    has_date = bool(pre_fields.get("issue_date"))
    has_doc = bool(pre_fields.get("doc_number"))
    has_vendor = bool(pre_fields.get("vendor"))
    has_tax_id = bool(pre_fields.get("vendor_tax_id"))
    strong_count = sum([has_total, has_date, has_doc, has_vendor, has_tax_id])

    min_strong_fields = max(1, int(processing_cfg.get("pre_extract_min_strong_fields") or 3))
    min_confidence = float(processing_cfg.get("pre_extract_min_confidence") or 0.62)
    confidence = min(0.62 + max(strong_count - 3, 0) * 0.08, 0.82)

    return {
        "has_total": has_total,
        "has_date": has_date,
        "has_doc": has_doc,
        "has_vendor": has_vendor,
        "has_tax_id": has_tax_id,
        "strong_count": strong_count,
        "min_strong_fields": min_strong_fields,
        "min_confidence": min_confidence,
        "confidence": confidence,
        "skip_ai": bool(
            has_total and strong_count >= min_strong_fields and confidence >= min_confidence
        ),
    }


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


def _classify_structured_by_filename(
    filename: str,
    patterns: dict[str, list[str]],
) -> str | None:
    """Infer doc_type for structured files (Excel/CSV) from the filename.

    Only intended for promoting STRUCTURED → a specific type when column analysis
    was insufficient. Uses word-boundary matching against structured_filename_patterns.
    Priority order ensures specific types win over more generic ones.
    """
    import unicodedata as _ud

    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    norm = _ud.normalize("NFKD", stem.lower())
    norm = "".join(ch for ch in norm if not _ud.combining(ch))
    norm = re.sub(r"[_\-\.\s]+", " ", norm).strip()

    _PRIORITY = [
        "EXPENSE",
        "BANK_MOVEMENTS",
        "BANK_STATEMENT",
        "PAYROLL",
        "COSTING",
        "SALES",
    ]
    for doc_type in _PRIORITY:
        for keyword in patterns.get(doc_type, []):
            kw = keyword.lower().strip()
            if not kw:
                continue
            if re.search(r"(?:^|(?<=\s))" + re.escape(kw) + r"(?=\s|$)", norm):
                return doc_type
    return None


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


def _build_ai_attempt_fingerprint(
    *,
    model_used: Any,
    content: str,
    timeout_override: float | None,
    strategy: str,
    force_vision: bool,
) -> dict[str, Any]:
    normalized_content = str(content or "").strip()
    normalized_model = str(model_used or "").strip().lower()
    return {
        "model": normalized_model,
        "content_sha1": (
            sha1(normalized_content.encode("utf-8"), usedforsecurity=False).hexdigest()
            if normalized_content
            else ""
        ),
        "timeout": round(float(timeout_override or 0.0), 3),
        "strategy": str(strategy or "").strip().lower(),
        "force_vision": bool(force_vision),
    }


def _should_skip_useless_retry(
    *,
    previous_analysis: dict[str, Any],
    previous_attempt: dict[str, Any],
    next_attempt: dict[str, Any],
) -> tuple[bool, str]:
    error_text = " ".join(
        str(previous_analysis.get(key) or "") for key in ("error", "raw_response", "reasoning")
    ).lower()
    if "timeout" not in error_text:
        return False, ""

    same_model = previous_attempt.get("model") == next_attempt.get("model")
    same_input = previous_attempt.get("content_sha1") == next_attempt.get("content_sha1")
    same_strategy = previous_attempt.get("timeout") == next_attempt.get(
        "timeout"
    ) and previous_attempt.get("strategy") == next_attempt.get("strategy")
    if same_model and same_input and same_strategy:
        return True, "timeout_same_model_input_strategy"
    return False, ""


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


def _normalize_line_item_identity_value(value: Any) -> str:
    raw = " ".join(str(value or "").split()).strip().lower()
    if not raw:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", raw).strip()


def _line_item_identity(item: dict[str, Any]) -> tuple[str, str, str]:
    barcode = re.sub(r"[^0-9]", "", str(item.get("barcode") or ""))
    product_code = _normalize_line_item_identity_value(item.get("product_code"))
    description = _normalize_line_item_identity_value(
        item.get("description") or item.get("concept")
    )
    return barcode, product_code, description


def _normalize_visual_line_item_text(value: Any) -> str | None:
    raw = " ".join(str(value or "").split()).strip()
    if not raw:
        return None
    normalized = _normalize_invoice_description_strict(raw) or raw
    if raw.endswith("/") and normalized and not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def _line_item_has_positive_amount(item: dict[str, Any]) -> bool:
    total_price = safe_floatish(item.get("total_price"))
    unit_price = safe_floatish(item.get("unit_price"))
    amount = safe_floatish(item.get("amount"))
    return any(
        value is not None and float(value) > 0.0 for value in (total_price, unit_price, amount)
    )


def _line_item_is_degraded_duplicate(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    return not _line_item_has_positive_amount(candidate) and _line_item_has_positive_amount(
        existing
    )


def _sanitize_visual_line_items(line_items_value: Any, *, format_hint: str) -> list[dict[str, Any]]:
    items = line_items_value if isinstance(line_items_value, list) else []
    if not items:
        return []

    normalized_format = str(format_hint or "").strip().upper()
    should_normalize_invoice_text = normalized_format in {"IMAGE_OCR", "PDF_OCR"}

    cleaned: list[dict[str, Any]] = []
    seen_index_by_identity: dict[tuple[str, str, str], int] = {}

    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)

        if should_normalize_invoice_text:
            for key in ("description", "concept"):
                normalized_value = _normalize_visual_line_item_text(item.get(key))
                if normalized_value:
                    item[key] = normalized_value
            if not item.get("concept") and item.get("description"):
                item["concept"] = item["description"]

        identity = _line_item_identity(item)
        if any(identity):
            existing_index = seen_index_by_identity.get(identity)
            if existing_index is not None:
                existing_item = cleaned[existing_index]
                if _line_item_is_degraded_duplicate(item, existing_item):
                    continue
                if _line_item_is_degraded_duplicate(existing_item, item):
                    cleaned[existing_index] = item
                continue
            seen_index_by_identity[identity] = len(cleaned)

        cleaned.append(item)

    return cleaned


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
    ocr_runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    """Drop noisy OCR fallback values and apply high-evidence repairs."""
    cleaned = dict(fallback_fields or {})
    if not cleaned:
        return {}
    original_numeric_values = {
        key: safe_floatish(cleaned.get(key)) for key in ("subtotal", "tax_amount", "total_amount")
    }

    removed: list[str] = []

    for key, original_value in original_numeric_values.items():
        if original_value is None:
            continue
        current_value = safe_floatish(cleaned.get(key))
        if current_value is None:
            cleaned[key] = original_value

    for key in ("subtotal", "tax_amount", "total_amount"):
        parsed_value = safe_floatish(cleaned.get(key))
        if parsed_value is None:
            cleaned.pop(key, None)
            continue
        cleaned[key] = parsed_value

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
        raw = re.split(
            r"\b20\d{2}-\d{2}-\d{2}t\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2})?\b",
            raw,
            maxsplit=1,
            flags=re.I,
        )[0].strip()
        raw = re.split(r"\b(?:ambiente|emision|fecha|ruc)\b", raw, maxsplit=1, flags=re.I)[
            0
        ].strip()
        if not raw:
            continue
        normalized_raw = unicodedata.normalize("NFD", raw)
        normalized_raw = "".join(
            ch for ch in normalized_raw if unicodedata.category(ch) != "Mn"
        ).lower()
        normalized_raw = " ".join(normalized_raw.split())
        strong_alpha_tokens = re.findall(r"[A-Za-zÀ-ÿ]{3,}", raw)
        company_suffix = re.search(
            r"\b(?:s\.?\s*a\.?|ltda\.?|cia\.?|compania|company|corp\.?|inc\.?|s\.?\s*r\.?\s*l\.?|sas)\b",
            raw,
            flags=re.I,
        )
        alpha = sum(1 for ch in raw if ch.isalpha())
        weird = sum(1 for ch in raw if not (ch.isalnum() or ch.isspace() or ch in ".,&-/()"))
        alpha_ratio = alpha / max(len(raw), 1)
        weird_ratio = weird / max(len(raw), 1)
        if (
            alpha < 4
            or alpha_ratio < 0.3
            or weird_ratio > 0.12
            or (len(strong_alpha_tokens) < 2 and not company_suffix)
            or (
                "factura" in normalized_raw
                and ("simplificada" in normalized_raw or "simplif" in normalized_raw)
            )
            or "ticket" in normalized_raw
            or "para el cliente" in normalized_raw
        ):
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


def _repair_pre_extracted_fields(
    pre_fields: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    prompt_config: dict[str, Any] | None,
    ocr_runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply the same OCR evidence repairs to pre-extract fields used in fallback paths.

    This keeps the deterministic fast path consistent with the repaired fallback path:
    if OCR clearly contains a date, tax ID or stronger invoice evidence, those fields
    must be available before deciding whether AI can be skipped.
    """
    cleaned = _sanitize_text_fallback_fields(
        pre_fields,
        content=content,
        format_hint=format_hint,
        prompt_config=prompt_config,
        ocr_runtime=ocr_runtime,
    )
    if not cleaned:
        return {}

    parsed = {"doc_type": "OTHER", "fields": dict(cleaned)}
    _apply_high_evidence_ocr_repairs(
        parsed,
        content=content,
        format_hint=format_hint,
        prompt_config=prompt_config,
        ai_runtime=None,
        ocr_runtime=ocr_runtime,
    )
    repaired_fields = parsed.get("fields")
    if not isinstance(repaired_fields, dict):
        return cleaned

    final_cleaned = _sanitize_text_fallback_fields(
        repaired_fields,
        content=content,
        format_hint=format_hint,
        prompt_config=prompt_config,
        ocr_runtime=ocr_runtime,
    )
    if not final_cleaned:
        return {}

    vendor_tax_id = str(final_cleaned.get("vendor_tax_id") or "").strip()
    customer_tax_id = str(final_cleaned.get("customer_tax_id") or "").strip()
    if vendor_tax_id and customer_tax_id and vendor_tax_id == customer_tax_id:
        final_cleaned.pop("customer_tax_id", None)

    line_items_list = _sanitize_visual_line_items(
        final_cleaned.get("line_items"),
        format_hint=format_hint,
    )
    if line_items_list:
        final_cleaned["line_items"] = line_items_list
    else:
        final_cleaned.pop("line_items", None)

    current_concept = str(final_cleaned.get("concept") or "").strip()
    if _looks_like_noisy_scalar_text(current_concept, field_name="concept"):
        for item in line_items_list:
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or item.get("concept") or "").strip()
            if description and not _looks_like_noisy_scalar_text(description, field_name="concept"):
                final_cleaned["concept"] = description[:140]
                break
        else:
            final_cleaned.pop("concept", None)

    current_vendor = str(final_cleaned.get("vendor") or "").strip()
    if not current_vendor or _looks_like_noisy_scalar_text(current_vendor, field_name="vendor"):
        # Use the unified vendor extractor so the AI repair path, the OCR text
        # fallback and this post-processing step share the same inference.
        from .field_extractors import extract_vendor_name as _unified_extract_vendor_name

        ocr_vendor = _unified_extract_vendor_name(text=content, ocr_runtime=ocr_runtime)
        if ocr_vendor and not _looks_like_noisy_scalar_text(ocr_vendor, field_name="vendor"):
            final_cleaned["vendor"] = ocr_vendor[:140]
        else:
            final_cleaned.pop("vendor", None)

    total_amount = safe_floatish(final_cleaned.get("total_amount"))
    subtotal = safe_floatish(final_cleaned.get("subtotal"))
    tax_amount = safe_floatish(final_cleaned.get("tax_amount"))
    line_items_total = 0.0
    line_items_with_amount = 0
    for item in line_items_list:
        if not isinstance(item, dict):
            continue
        item_total = safe_floatish(item.get("total_price"))
        if item_total is None:
            item_total = safe_floatish(item.get("amount"))
        if item_total is None:
            continue
        line_items_total += float(item_total)
        line_items_with_amount += 1

    if (
        total_amount is None
        and not str(final_cleaned.get("issue_date") or "").strip()
        and not line_items_list
    ):
        final_cleaned.pop("subtotal", None)
        final_cleaned.pop("tax_amount", None)
    elif total_amount is not None:
        if tax_amount is not None and (tax_amount < 0 or tax_amount > total_amount + 0.01):
            final_cleaned.pop("tax_amount", None)
            tax_amount = None
        if subtotal is not None and (subtotal <= 0 or subtotal > total_amount + 0.01):
            final_cleaned.pop("subtotal", None)
            subtotal = None
        if subtotal is not None and tax_amount is not None:
            combined = subtotal + tax_amount
            if abs(combined - total_amount) > max(1.0, total_amount * 0.05):
                final_cleaned.pop("tax_amount", None)
                tax_amount = None
        if (
            subtotal is not None
            and line_items_with_amount > 0
            and abs(line_items_total - total_amount) <= max(1.0, total_amount * 0.02)
            and subtotal < (total_amount * 0.75)
        ):
            final_cleaned.pop("subtotal", None)

    return final_cleaned


def _looks_like_noisy_scalar_text(value: Any, *, field_name: str) -> bool:
    cfg = load_ocr_runtime_config(None)
    raw = " ".join(str(value or "").split()).strip()
    if not raw:
        return True

    normalized = unicodedata.normalize("NFD", raw)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").lower()
    normalized = " ".join(normalized.split())

    alpha = sum(1 for ch in raw if ch.isalpha())
    weird = sum(1 for ch in raw if not (ch.isalnum() or ch.isspace() or ch in ".,&-/()"))
    alpha_ratio = alpha / max(len(raw), 1)
    weird_ratio = weird / max(len(raw), 1)
    strong_alpha_tokens = re.findall(r"[A-Za-z\u00C0-\u017F]{3,}", raw)
    short_tokens = [
        token for token in re.findall(r"[A-Za-z\u00C0-\u017F]+", raw) if len(token) <= 2
    ]

    if field_name == "vendor":
        min_alpha = int(cfg.get("vendor_noise_min_alpha") or 0)
        min_alpha_ratio = float(cfg.get("vendor_noise_min_alpha_ratio") or 0.0)
        max_weird_ratio = float(cfg.get("vendor_noise_max_weird_ratio") or 1.0)
        min_strong_tokens = int(cfg.get("vendor_noise_min_strong_tokens") or 0)
        max_short_tokens = int(cfg.get("vendor_noise_max_short_tokens") or 0)
        reject_tokens = {
            str(token).strip().lower()
            for token in (cfg.get("vendor_noise_reject_tokens") or [])
            if str(token).strip()
        }
        reject_prefixes = {
            str(token).strip().lower()
            for token in (cfg.get("vendor_noise_reject_prefixes") or [])
            if str(token).strip()
        }
        if (
            alpha < min_alpha
            or alpha_ratio < min_alpha_ratio
            or weird_ratio > max_weird_ratio
            or len(strong_alpha_tokens) < min_strong_tokens
            or len(short_tokens) >= max(max_short_tokens, len(strong_alpha_tokens))
        ):
            return True
        if any(token in normalized for token in reject_tokens):
            return True
        if any(normalized.startswith(prefix) for prefix in reject_prefixes):
            return True
        return False

    if field_name == "concept":
        min_alpha = int(cfg.get("concept_noise_min_alpha") or 0)
        min_alpha_ratio = float(cfg.get("concept_noise_min_alpha_ratio") or 0.0)
        max_weird_ratio = float(cfg.get("concept_noise_max_weird_ratio") or 1.0)
        min_strong_tokens = int(cfg.get("concept_noise_min_strong_tokens") or 0)
        max_short_tokens_factor = float(cfg.get("concept_noise_max_short_tokens_factor") or 1.0)
        small_token_max_len = int(cfg.get("concept_noise_small_token_max_len") or 0)
        small_token_max_count = int(cfg.get("concept_noise_small_token_max_count") or 0)
        reject_chars = {
            str(char) for char in (cfg.get("concept_noise_reject_chars") or []) if str(char)
        }
        reject_tokens = {
            str(token).strip().lower()
            for token in (cfg.get("concept_noise_reject_tokens") or [])
            if str(token).strip()
        }
        reject_prefixes = [
            str(token).strip().lower()
            for token in (cfg.get("concept_noise_reject_prefixes") or [])
            if str(token).strip()
        ]
        reject_token_pairs = [
            [str(item).strip().lower() for item in pair[:2]]
            for pair in (cfg.get("concept_noise_reject_token_pairs") or [])
            if isinstance(pair, list) and len(pair) >= 2
        ]

        if alpha < min_alpha or alpha_ratio < min_alpha_ratio or weird_ratio > max_weird_ratio:
            return True
        all_tokens = re.findall(r"[A-Za-z\u00C0-\u017F]+", raw)
        if len(strong_alpha_tokens) < min_strong_tokens or len(short_tokens) >= max(
            2, int(len(strong_alpha_tokens) * max_short_tokens_factor)
        ):
            return True
        if (
            len(all_tokens) <= small_token_max_count
            and max((len(token) for token in all_tokens), default=0) <= small_token_max_len
        ):
            return True
        if any(ch in raw for ch in reject_chars):
            return True
        if any(token in normalized for token in reject_tokens):
            return True
        if any(normalized.startswith(prefix) for prefix in reject_prefixes):
            return True
        if any(all(token in normalized for token in pair) for pair in reject_token_pairs):
            return True
        return False

    return False


def _prefer_text_candidate_over_existing(*, field_name: str, existing: Any, candidate: Any) -> bool:
    if candidate in (None, "", [], {}):
        return False
    if existing in (None, "", [], {}):
        return True

    existing_raw = " ".join(str(existing).split()).strip()
    candidate_raw = " ".join(str(candidate).split()).strip()
    if not candidate_raw:
        return False

    if field_name == "vendor":
        if _looks_like_noisy_scalar_text(
            existing_raw, field_name="vendor"
        ) and not _looks_like_noisy_scalar_text(candidate_raw, field_name="vendor"):
            return True
        return False

    if field_name == "concept":
        if _looks_like_noisy_scalar_text(
            existing_raw, field_name="concept"
        ) and not _looks_like_noisy_scalar_text(candidate_raw, field_name="concept"):
            return True
        return False

    return False


def _build_low_evidence_visual_review_analysis(
    *,
    filename: str,
    format_hint: str,
    pre_fields: dict[str, Any],
    ocr_quality_score: float | None,
    processing_cfg: dict[str, Any],
) -> dict[str, Any]:
    min_chars = max(1, int(processing_cfg.get("ocr_text_sufficient_min_chars") or 500))
    quality_threshold = float(processing_cfg.get("ocr_quality_vision_threshold") or 0.45)
    user_message = (
        "La imagen no tiene evidencia suficiente para una extracción fiable. "
        "Saca una foto mas nitida o completa los datos manualmente antes de guardar."
    )
    return {
        "doc_type": "OTHER",
        "confidence": 0.2,
        "reasoning": (
            "OCR sin evidencia mínima fiable para extracción automática. "
            "Se evita IA pesada porque no hay campos fuertes para rescatar."
        ),
        "is_table": False,
        "columns": [],
        "fields": pre_fields,
        "raw_response": "reason=low_evidence_visual_review",
        "model_used": "deterministic-low-evidence",
        "analysis_path": "low_evidence_review",
        "requires_review": True,
        "warnings": [
            {
                "quality_gate": "rejected_for_extraction",
                "quality_score": ocr_quality_score,
                "quality_threshold": quality_threshold,
                "chars_threshold": min_chars,
                "user_message": user_message,
            }
        ],
        "user_message": user_message,
        "filename": filename,
        "format_hint": format_hint,
    }


def _field_keys_for_reprocess(data: dict[str, Any] | None) -> list[str]:
    if not isinstance(data, dict):
        return []
    return sorted(
        str(key)
        for key, value in data.items()
        if not str(key).startswith("_") and value not in (None, "", [], {})
    )


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
    pre_extracted_fields: dict[str, Any] | None = None,
    fallback_patterns: dict[str, Any],
    canonical_fields: dict[str, Any],
    prompt_config: dict[str, Any],
    db: Any = None,
    reprocess_mode: str = "fast",
    bypass_cache: bool = False,
    deep_reprocess_context: dict[str, Any] | None = None,
    deep_focus_fields: list[str] | None = None,
    timeout_override: float | None = None,
    force_vision: bool = False,
) -> dict[str, Any]:
    processing_cfg = load_processing_runtime_config(db)
    min_chars = max(1, int(processing_cfg.get("ocr_text_sufficient_min_chars") or 500))

    content_text = (content or "").strip()
    text_is_sufficient = len(content_text) >= min_chars
    structured_is_usable = bool(has_structured_rows or structured_data)
    _format_hint = str(format_hint or "").strip().upper()

    quality_warning: dict[str, Any] | None = None
    image_bytes = bytes(vision_image_bytes) if vision_image_bytes else None
    low_quality = False
    quality: dict[str, Any] | None = None

    if vision_image_bytes:
        ocr_runtime = load_ocr_runtime_config(db)
        quality = _estimate_text_quality(content_text, ocr_runtime=ocr_runtime)
        quality_threshold = float(ocr_runtime.get("ocr_min_quality") or 0.45)
        low_quality = quality["score"] <= quality_threshold

        if low_quality:
            quality_warning = {
                "quality_gate": "warning",
                "quality_score": quality["score"],
                "quality_threshold": quality_threshold,
                "chars": quality["chars"],
                "text_is_sufficient": text_is_sufficient,
                "structured_is_usable": structured_is_usable,
                "degraded_to_review": text_is_sufficient
                or structured_is_usable
                or reprocess_mode == "fast",
                "rejected_for_quality": False,
            }

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

    _prev_confidence_for_skip: float | None = None
    if isinstance(deep_reprocess_context, dict):
        _prev_result = deep_reprocess_context.get("previous_result") or {}
        if isinstance(_prev_result, dict):
            try:
                _v = _prev_result.get("confianza_clasificacion")
                _prev_confidence_for_skip = float(_v) if _v is not None else None
            except (TypeError, ValueError):
                _prev_confidence_for_skip = None

    _prev_was_good = _prev_confidence_for_skip is None or _prev_confidence_for_skip >= 0.75

    is_first_import = not isinstance(
        deep_reprocess_context, dict
    ) or not deep_reprocess_context.get("previous_result")

    logger.info(
        "DBG[C] ai_routing filename=%s mode=%s ai_invoked=%s is_first_import=%s "
        "text_is_sufficient=%s has_vision=%s _prev_was_good=%s has_structured=%s format=%s",
        filename,
        reprocess_mode,
        True,
        is_first_import,
        text_is_sufficient,
        bool(vision_image_bytes),
        _prev_was_good,
        has_structured_rows,
        _format_hint,
    )
    if is_first_import and str(reprocess_mode or "").strip().lower() == "fast":
        logger.info(
            "first_import_ai_forced=true filename=%s mode=%s text_is_sufficient=%s reason=first_import_guard",
            filename,
            reprocess_mode,
            text_is_sufficient,
        )
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
        pre_extracted_fields=pre_extracted_fields,
        db=db,
        reprocess_mode=reprocess_mode,
        bypass_cache=bypass_cache,
        deep_reprocess_context=deep_reprocess_context,
        deep_focus_fields=deep_focus_fields,
        timeout_override=timeout_override,
        force_vision=force_vision,
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


def _build_structured_payload(
    *,
    structured_rows: list[dict[str, Any]],
    structured_rows_all: list[dict[str, Any]],
    sheet_profiles: dict[str, Any] | None,
    sheet_metadata: dict[str, Any] | None,
    sheet_used: str | None,
    sheet_names: list[str],
    headers_norm: list[str],
    headers_display: list[str],
    recipe_name_detected: str | None,
    recipe_name_field_candidates: set[str],
    structured_output_limit: int,
    filename: str,
) -> tuple[dict[str, Any], str]:
    """Construye el payload estructurado para documentos tabulares (XLSX, CSV, XML…).

    Resuelve el nombre de receta (desde filas, metadata o fallback al nombre de archivo)
    y agrupa las filas por hoja.

    Returns:
        (payload, recipe_name_detected)
    """
    columnas = headers_display or headers_norm

    if recipe_name_detected is None:
        for row in structured_rows[:structured_output_limit]:
            if not isinstance(row, dict):
                continue
            for key in row.keys():
                if str(key or "").strip().lower() in recipe_name_field_candidates:
                    value = row.get(key)
                    if value:
                        recipe_name_detected = str(value).strip()
                        break
            if recipe_name_detected:
                break

    meta_for_sheet: dict[str, Any] | None = None
    if sheet_metadata:
        meta_for_sheet = sheet_metadata.get(sheet_used) or (
            sheet_metadata.get(sheet_names[0]) if sheet_names else None
        )

    if recipe_name_detected is None and meta_for_sheet:
        for key, value in meta_for_sheet.items():
            if str(key or "").strip().lower() in recipe_name_field_candidates and value:
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
        sheet_key = row.get("_sheet") or sheet_used or ""
        filas_por_hoja.setdefault(str(sheet_key), []).append(row)

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

    payload: dict[str, Any] = {
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
        payload["metadata"] = meta_for_sheet

    if filas_por_hoja:
        payload["filas_por_hoja"] = {
            key: value[:structured_output_limit] for key, value in filas_por_hoja.items()
        }
        payload["filas_por_hoja_count"] = filas_count

    return payload, recipe_name_detected


def _merge_structured_extraction(
    base_extracted: dict[str, Any],
    structured_payload: dict[str, Any],
) -> dict[str, Any]:
    """Fusiona los campos extraídos por IA con el payload tabular estructurado.

    El payload estructurado toma precedencia en claves duplicadas.
    Preserva los line_items del resultado IA si el payload no produjo ninguno.
    """
    previous_line_items = (
        list(base_extracted.get("line_items") or [])
        if isinstance(base_extracted.get("line_items"), list)
        else []
    )
    merged = {**base_extracted, **structured_payload}
    if previous_line_items and not merged.get("line_items"):
        merged["line_items"] = previous_line_items
    return merged


async def process_import_document(
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
    recipe_context: RecipeContext | None = None,
) -> DocumentProcessingResult:
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
    _doc_format = str(extraction.get("format", tipo_archivo) or "").upper()

    has_structured = bool(
        structured
        and isinstance(structured, list)
        and sheet_profiles
        and _doc_format not in {"XML_PARSE_ERROR", "EXCEL_ERROR"}
    )
    structured_rows_all: list[dict[str, Any]] = structured if isinstance(structured, list) else []
    structured_rows: list[dict[str, Any]] = list(structured_rows_all)

    headers_norm: list[str] = []
    headers_display: list[str] = []
    structured_output_limit = max(1, int(processing_cfg.get("structured_output_rows_limit") or 200))

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

    is_image_doc = tipo_archivo.upper() in _get_visual_formats(db)
    is_scanned_pdf = tipo_archivo == "PDF" and extraction.get("format") == "PDF_OCR"
    vision_image_bytes = extraction.get("vision_image_bytes")
    if not isinstance(vision_image_bytes, (bytes, bytearray)):
        vision_image_bytes = file_bytes if is_image_doc else None

    recipe_snapshot = _load_snapshot(db, local_snapshot_id)
    cached_analysis = None
    text_cached_analysis_run = None
    analysis_recipe_config = dict(local_recipe_config or {})
    analysis: dict[str, Any] = {}

    if recipe_snapshot:
        if has_structured:
            cached_analysis = get_snapshot_learning(recipe_snapshot, structured_only=True)
            # Cambio 2: no aceptar cache semánticamente vacío (base_keys=[], line_items=0).
            if cached_analysis is not None:
                _cache_base_keys = cached_analysis.get("base_keys") or []
                _cache_line_items = cached_analysis.get("line_items") or []
                if not _cache_base_keys and not _cache_line_items:
                    logger.info(
                        "snapshot_cache_rejected doc_id=%s reason=empty_semantic_result "
                        "base_keys=%s line_items_count=0",
                        doc.id,
                        _cache_base_keys,
                    )
                    cached_analysis = None
        else:
            text_cached_analysis_run = get_snapshot_learning(recipe_snapshot, structured_only=False)

    runtime_config_started_at = time.perf_counter()
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    field_aliases_early = get_field_aliases(db, tenant_id=tenant_id)
    amount_label_cfg = load_amount_label_config(db)
    prompt_config = load_prompt_config(db)
    ocr_runtime = load_ocr_runtime_config(db)
    fallback_patterns = load_doc_type_patterns(db)
    doc_type_resolution_cfg = load_doc_type_resolution_config(db)
    classification_threshold = load_classification_threshold(db)
    learning_ctrl = load_learning_control(db)
    pdf_table_cfg = load_pdf_table_parse_config(db)
    ai_enabled = bool(processing_cfg.get("ai_enabled", True))
    _set_stage_timing(stage_timings, "runtime_config_load", runtime_config_started_at)

    _rc_for_run = dict(local_recipe_config or {})
    doc_type_hint_min_confidence = float(processing_cfg.get("doc_type_hint_min_confidence") or 0.65)
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

    # Skip LLM only when we already have a real semantic type from a previous run.
    # "STRUCTURED" and "OTHER" are placeholders, not semantic types: they mean the LLM
    # never classified this document properly, so we must still run it to get line_items,
    # kv_pairs, column_profiles and a meaningful doc_type.
    _has_semantic_hint = bool(_rc_for_run.get("doc_type_hint")) and str(
        _rc_for_run.get("doc_type_hint", "")
    ).upper() not in ("", "STRUCTURED", "OTHER")
    # Los formatos XML de factura electrónica llevan su propio tipo de documento en el
    # header parseado, por lo que no necesitan un hint semántico externo para saltar el LLM.
    _is_xml_invoice_format = _doc_format in _get_xml_invoice_formats(db)
    _skip_ai_for_structured = (
        has_structured
        and _doc_format in _get_structured_skip_formats(db)
        and not force_clean_reimport
        and (_has_semantic_hint or _is_xml_invoice_format or not ai_enabled)
    )
    # ── Señales post-OCR para routing de carril ────────────────────────────
    _reprocess_ctx = recipe_context.reprocess_context or {}
    _prev_result_ctx = _reprocess_ctx.get("previous_result") or {}
    _is_first_import = not bool(isinstance(_prev_result_ctx, dict) and _prev_result_ctx)
    _prev_confidence: float | None = None
    if isinstance(_prev_result_ctx, dict) and _prev_result_ctx:
        try:
            _c = _prev_result_ctx.get("confianza_clasificacion")
            _prev_confidence = float(_c) if _c is not None else None
        except (TypeError, ValueError):
            _prev_confidence = None

    _text_is_sufficient_for_lane = len(str(text or "").strip()) >= max(
        1, int(processing_cfg.get("ocr_text_sufficient_min_chars") or 500)
    )
    _has_vision_for_lane = bool(vision_image_bytes) or tipo_archivo in (
        "JPG",
        "JPEG",
        "PNG",
        "IMG",
        "HEIC",
        "WEBP",
        "IMAGE_OCR",
    )

    _ocr_quality_score: float | None = extraction.get("ocr_quality_score")

    lane_decision = decide_processing_lane(
        doc_format=_doc_format,
        has_structured=has_structured,
        has_vision=_has_vision_for_lane,
        text_is_sufficient=_text_is_sufficient_for_lane,
        has_semantic_hint=_has_semantic_hint,
        has_cached_analysis=bool(cached_analysis),
        is_first_import=_is_first_import,
        previous_confidence=_prev_confidence,
        deep_reprocess=deep_reprocess,
        processing_cfg=processing_cfg,
        ocr_quality_score=_ocr_quality_score,
    )
    logger.info(
        "processing_lane doc_id=%s lane=%s phase_timeout=%.1fs force_vision=%s vision_first=%s reasons=%s",
        doc.id,
        lane_decision.lane,
        lane_decision.timeout_secs,
        lane_decision.force_vision,
        lane_decision.vision_first,
        lane_decision.reasons,
    )

    # Log específico para PDFs para observabilidad de estrategia de fases
    if _doc_format in {"PDF", "PDF_OCR"}:
        logger.info(
            "pdf_strategy doc_id=%s format=%s primary=%s secondary=%s "
            "phase_timeout=%.1fs ocr_quality=%s",
            doc.id,
            _doc_format,
            "vision" if lane_decision.vision_first else "text",
            "text_if_needed" if lane_decision.vision_first else "vision_if_needed",
            lane_decision.timeout_secs,
            f"{_ocr_quality_score:.2f}" if _ocr_quality_score is not None else "unknown",
        )

    # Log específico para CSV/XML resueltos sin deep
    if (
        _doc_format in {"CSV", "JSON", "XML", "XML_UBL", "XML_FACTURAE"}
        and lane_decision.lane == "fast"
    ):
        logger.info(
            "structured_or_parser_skip_deep doc_id=%s filename=%s format=%s reason=%s",
            doc.id,
            filename,
            _doc_format,
            ",".join(lane_decision.reasons),
        )

    # Flags de escalado (se actualizan si fast→deep escala inline)
    _lane_escalated = False
    _lane_escalation_reason: str | None = None

    if cached_analysis:
        analysis = {
            **cached_analysis,
            "fields": {},
            "is_table": True,
            "columns": [],
            "model_used": "snapshot-cache",
            "prompt_full": "",
            "raw_response": "snapshot-cache",
            "analysis_path": "ok_snapshot_cache",
        }
    elif _skip_ai_for_structured:
        if _is_xml_invoice_format and sheet_metadata:
            # Para XML_FACTURAE / XML_UBL: leer tipo de documento y campos del header parseado.
            # sheet_metadata tiene forma {sheet_name: kv_pairs}, usamos sheet_used como clave.
            _xml_meta_kv: dict[str, Any] = sheet_metadata.get(sheet_used or "") or (
                next(iter(sheet_metadata.values()), {}) if sheet_metadata else {}
            )
            _xml_tipo = str(_xml_meta_kv.get("tipo_documento") or "").upper()
            _hint_doc_type = _XML_TIPO_DOCUMENTO_MAP.get(_xml_tipo, "INVOICE")
            _xml_fields: dict[str, Any] = {}
            for _xml_key, _canonical_key in _XML_HEADER_TO_CANONICAL.items():
                _xml_val = _xml_meta_kv.get(_xml_key)
                if (
                    _xml_val not in (None, "", "0", "0.00", "0.0")
                    and _canonical_key not in _xml_fields
                ):
                    _xml_fields[_canonical_key] = _xml_val
            _xml_confidence = 0.90 if _xml_fields else 0.72
        else:
            _hint_doc_type = str(_rc_for_run.get("doc_type_hint") or "").upper() or "STRUCTURED"
            _xml_fields = {}
            _xml_confidence = 0.82
        analysis = {
            "doc_type": _hint_doc_type,
            "confidence": _xml_confidence,
            "reasoning": f"Structured data ({_doc_format}) parsed directly; LLM skipped.",
            "is_table": not _is_xml_invoice_format,
            "columns": headers_display or headers_norm,
            "fields": _xml_fields,
            "raw_response": "reason=structured_parse_skip",
            "model_used": "structured-parse-skip",
            "analysis_path": "ok_structured",
            "requires_review": False,
        }
        logger.info(
            "structured_parse_skip filename=%s format=%s doc_type=%s fields=%s",
            filename,
            _doc_format,
            _hint_doc_type,
            list(_xml_fields.keys()) if _xml_fields else [],
        )
    else:
        # ── Pre-extracción determinista (regex) ANTES del LLM ─────────────────
        # Para PDF, PDF_OCR e imágenes con texto OCR: extraemos campos con regex
        # (invoice_rescue + field_aliases de BD). Si encontramos ≥3 campos clave
        # (total + fecha/doc_number/vendor/tax_id) saltamos el LLM completamente.
        # Esto evita esperar 5-9 min de CPU con qwen:8b cuando el regex ya extrajo
        # lo que necesitamos. deep_reprocess siempre pasa por LLM (el usuario lo pidió).
        _pre_fields: dict[str, Any] = {}
        _pre_skipped_ai = False
        _PRE_EXTRACT_FORMATS = {"PDF", "PDF_OCR", "TXT", "IMAGE_OCR"}

        if text and text.strip() and _doc_format in _PRE_EXTRACT_FORMATS and not deep_reprocess:
            try:
                _rescue = invoice_rescue_from_ocr(text, existing_fields=_pre_fields)
                if isinstance(_rescue, dict):
                    _pre_fields.update(
                        {k: v for k, v in _rescue.items() if v not in (None, "", [], {})}
                    )
            except Exception as _exc:
                logger.debug("pre_extract rescue error (non-fatal): %s", _exc)
            try:
                _tf = extract_fields_from_text(
                    ocr_text=text,
                    canonical_fields=canonical_fields,
                    field_aliases=field_aliases_early,
                    amount_labels=amount_label_cfg,
                    pdf_config=pdf_table_cfg,
                    page_texts=extraction.get("page_texts"),
                )
                if isinstance(_tf, dict):
                    for _k, _v in _tf.items():
                        if _v in (None, "", [], {}):
                            continue
                        if _k not in _pre_fields or _prefer_text_candidate_over_existing(
                            field_name=_k,
                            existing=_pre_fields.get(_k),
                            candidate=_v,
                        ):
                            _pre_fields[_k] = _v
            except Exception as _exc:
                logger.debug("pre_extract text error (non-fatal): %s", _exc)

            _pre_fields = _repair_pre_extracted_fields(
                _pre_fields,
                content=text,
                format_hint=_doc_format,
                prompt_config=prompt_config,
                ocr_runtime=ocr_runtime,
            )

            _pre_decision = _pre_extract_route_decision(
                pre_fields=_pre_fields,
                processing_cfg=processing_cfg,
            )
            _has_total = bool(_pre_decision["has_total"])
            _has_date = bool(_pre_decision["has_date"])
            _has_doc = bool(_pre_decision["has_doc"])
            _has_vendor = bool(_pre_decision["has_vendor"])
            _has_tax_id = bool(_pre_decision["has_tax_id"])
            _strong_count = int(_pre_decision["strong_count"])

            def _resolve_native_doc_type(
                base_doc_type: str, base_confidence: float
            ) -> tuple[str, float, str, str | None]:
                return promote_doc_type_from_text_fallback(
                    current_doc_type=base_doc_type,
                    current_confidence=base_confidence,
                    current_reasoning="Native deterministic extraction only.",
                    fields=_pre_fields,
                    content=text,
                    filename=filename,
                    resolution_config=doc_type_resolution_cfg,
                    fallback_patterns=fallback_patterns,
                )

            _native_doc_type = str(_rc_for_run.get("doc_type_hint") or "").upper()
            if not _native_doc_type:
                _native_doc_type = "STRUCTURED" if has_structured else "OTHER"
            _native_confidence = float(_pre_decision["confidence"] if _pre_fields else 0.35)
            _native_doc_type, _native_confidence, _native_reasoning, _native_reason_tag = (
                _resolve_native_doc_type(
                    _native_doc_type,
                    _native_confidence,
                )
            )

            # Corrección conservadora por nombre de fichero (solo para razones débiles o
            # keyword genérico). No toca tipos fuertes (invoice_like_line_items, payroll_*).
            # Garantiza requires_review=True al bajar la confianza por debajo del umbral.
            _fn_stem_norm = re.sub(r"[_\-\.\s]+", " ", filename.rsplit(".", 1)[0].lower()).strip()
            if (
                _native_doc_type == "INVOICE"
                and _native_reason_tag in ("invoice_keyword", "invoice_like_fields")
                and re.search(r"(?:^|(?<=\s))(?:receipt|recibo)(?=\s|$)", _fn_stem_norm)
            ):
                _native_doc_type = "RECEIPT"
                _native_confidence = min(_native_confidence, 0.55)
                _native_reasoning = (
                    f"Corrección por nombre de fichero '{filename}': "
                    f"clasificado como RECEIPT (texto sugería INVOICE via {_native_reason_tag})."
                )
                _native_reason_tag = "filename_receipt_correction"
                logger.info(
                    "ocr_filename_correction filename=%s corrected=RECEIPT was=INVOICE reason=%s",
                    filename,
                    "invoice_keyword",
                )
            elif (
                _native_doc_type == "RECEIPT"
                and _native_reason_tag
                in ("receipt_like_fields", "receipt_keyword", "minimal_receipt_fields")
                and re.search(r"(?:^|(?<=\s))(?:sales|ventas|venta)(?=\s|$)", _fn_stem_norm)
            ):
                _native_doc_type = "SALES"
                _native_confidence = min(_native_confidence, 0.55)
                _native_reasoning = (
                    f"Corrección por nombre de fichero '{filename}': "
                    f"clasificado como SALES (texto sugería RECEIPT via {_native_reason_tag})."
                )
                _native_reason_tag = "filename_sales_correction"
                logger.info(
                    "ocr_filename_correction filename=%s corrected=SALES was=RECEIPT reason=%s",
                    filename,
                    _native_reason_tag,
                )

            if _native_reason_tag:
                logger.info(
                    "native_doc_type_promoted filename=%s format=%s doc_type=%s reason=%s fields=%s",
                    filename,
                    _doc_format,
                    _native_doc_type,
                    _native_reason_tag,
                    sorted(_pre_fields.keys()),
                )

            _line_items_present = bool(
                _pre_fields.get("line_items")
                if isinstance(_pre_fields.get("line_items"), list)
                else []
            )
            _has_primary_saveable_evidence = (
                safe_floatish(_pre_fields.get("total_amount")) is not None
                or bool(str(_pre_fields.get("issue_date") or "").strip())
                or _line_items_present
            )

            _low_evidence_visual = (
                _doc_format in (_get_visual_formats(db) | {"PDF_OCR"})
                and not has_structured
                and not _pre_decision["skip_ai"]
                and (
                    (
                        _strong_count == 0
                        and not _line_items_present
                        and (
                            _ocr_quality_score is None
                            or _ocr_quality_score
                            < float(processing_cfg.get("ocr_quality_vision_threshold") or 0.45)
                        )
                    )
                    or (_strong_count < 3 and not _has_primary_saveable_evidence)
                )
            )

            if _low_evidence_visual:
                analysis = _build_low_evidence_visual_review_analysis(
                    filename=filename,
                    format_hint=_doc_format,
                    pre_fields=_pre_fields,
                    ocr_quality_score=_ocr_quality_score,
                    processing_cfg=processing_cfg,
                )
                _pre_skipped_ai = True
                logger.info(
                    "low_evidence_visual_review filename=%s format=%s fields=%s strong_count=%s ocr_quality=%s",
                    filename,
                    _doc_format,
                    sorted(_pre_fields.keys()),
                    _strong_count,
                    f"{_ocr_quality_score:.2f}" if _ocr_quality_score is not None else "unknown",
                )
            elif not ai_enabled:
                _pre_doc_type = _native_doc_type
                _pre_confidence = _native_confidence
                analysis = {
                    "doc_type": _pre_doc_type,
                    "confidence": _pre_confidence,
                    "reasoning": _native_reasoning,
                    "is_table": bool(has_structured),
                    "columns": [],
                    "fields": _pre_fields,
                    "raw_response": "reason=native_deterministic_only",
                    "model_used": "deterministic-only",
                    "analysis_path": "ok_pre_extract",
                    "requires_review": _pre_confidence < classification_threshold,
                }
                _pre_skipped_ai = True
                logger.info(
                    "native_deterministic_only filename=%s format=%s doc_type=%s fields=%s",
                    filename,
                    _doc_format,
                    _pre_doc_type,
                    sorted(_pre_fields.keys()),
                )
            # Saltamos IA solo cuando la extracción nativa ya cubrió suficiente señal
            # y la confianza estimada supera el umbral configurable.
            # Saltamos IA solo cuando la extracción nativa ya cubrió suficiente señal
            # y la confianza estimada supera el umbral configurable.
            elif _pre_decision["skip_ai"]:
                _pre_doc_type = _native_doc_type
                if not _pre_doc_type or _pre_doc_type in ("OTHER", "STRUCTURED"):
                    if _has_doc or _has_tax_id:
                        _pre_doc_type = "INVOICE"
                    elif _has_date and _has_vendor:
                        _pre_doc_type = "INVOICE"
                    else:
                        _pre_doc_type = "RECEIPT"
                _pre_confidence = _native_confidence
                analysis = {
                    "doc_type": _pre_doc_type,
                    "confidence": _pre_confidence,
                    "reasoning": (
                        _native_reasoning
                        if _native_reason_tag
                        else (
                            f"Pre-extracción determinista: {_strong_count} campos clave "
                            "extraídos sin LLM."
                        )
                    ),
                    "is_table": False,
                    "columns": [],
                    "fields": _pre_fields,
                    "raw_response": "reason=pre_extract_skip_ai",
                    "model_used": "deterministic-preextract",
                    "analysis_path": "ok_pre_extract",
                    "requires_review": _pre_confidence < classification_threshold,
                }
                _pre_skipped_ai = True
                logger.info(
                    "pre_extract_skip_ai filename=%s format=%s doc_type=%s "
                    "fields=%s total=%s date=%s doc=%s vendor=%s tax_id=%s "
                    "strong_count=%s min_strong=%s min_confidence=%.2f confidence=%.2f",
                    filename,
                    _doc_format,
                    _pre_doc_type,
                    sorted(_pre_fields.keys()),
                    _has_total,
                    _has_date,
                    _has_doc,
                    _has_vendor,
                    _has_tax_id,
                    _strong_count,
                    _pre_decision["min_strong_fields"],
                    float(_pre_decision["min_confidence"]),
                    _pre_confidence,
                )

        if not ai_enabled and not analysis:
            _deterministic_doc_type = str(_rc_for_run.get("doc_type_hint") or "").upper()
            if not _deterministic_doc_type:
                _deterministic_doc_type = "STRUCTURED" if has_structured else "OTHER"
            _deterministic_confidence = (
                float(_pre_decision["confidence"]) if "_pre_decision" in locals() else 0.35
            )
            analysis = {
                "doc_type": _deterministic_doc_type,
                "confidence": _deterministic_confidence,
                "reasoning": "Native deterministic extraction only.",
                "is_table": bool(has_structured),
                "columns": [],
                "fields": _pre_fields,
                "raw_response": "reason=native_deterministic_fallback",
                "model_used": "deterministic-only",
                "analysis_path": "ok_pre_extract",
                "requires_review": _deterministic_confidence < classification_threshold,
            }
            _pre_skipped_ai = True
            logger.info(
                "native_deterministic_fallback filename=%s format=%s doc_type=%s fields=%s",
                filename,
                _doc_format,
                _deterministic_doc_type,
                sorted(_pre_fields.keys()),
            )

        if not _pre_skipped_ai:
            # ── Llamada al LLM ────────────────────────────────────────────────
            ai_primary_started_at = time.perf_counter()
            _send_vision = (lane_decision.force_vision or is_image_doc or is_scanned_pdf) and bool(
                vision_image_bytes
            )
            analysis = await analyze_document_fn(
                llm_content,
                filename,
                extraction.get("format", tipo_archivo),
                has_structured_rows=has_structured,
                recipe_config=_rc_for_run,
                structured_data=structured if has_structured else None,
                structured_metadata=sheet_metadata if has_structured else None,
                image_bytes=bytes(vision_image_bytes) if _send_vision else None,
                fallback_patterns=fallback_patterns,
                canonical_fields=canonical_fields,
                prompt_config=prompt_config,
                pre_extracted_fields=_pre_fields or None,
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
                timeout_override=lane_decision.timeout_secs,
                force_vision=lane_decision.force_vision,
                vision_first=lane_decision.vision_first,
            )
            _set_stage_timing(stage_timings, "ai_primary", ai_primary_started_at)
            analysis.setdefault("analysis_path", "ok_llm")
            # Guard: si el análisis terminó en fallback con tipo fuerte sin evidencia → degrada a OTHER
            analysis = _guard_fallback_doc_type(analysis, content=llm_content)

    normalize_analysis_started_at = time.perf_counter()
    normalized_analysis = _normalize_analysis_output(analysis)
    _set_stage_timing(stage_timings, "analysis_normalize", normalize_analysis_started_at)

    # ── Rescate de texto OCR cuando el LLM falló (timeout, error, fallback) ──
    # extract_fields_from_text usa los alias canónicos de la BD para extraer
    # campos escalares y line_items directamente del texto OCR, sin LLM.
    # Se activa solo en caminos de fallback para no interferir con extracciones OK.
    _ai_path = str(analysis.get("analysis_path") or "")
    if _ai_path in {"fallback", "fallback_error"} and text and text.strip():
        try:
            _ocr_fallback_fields = extract_fields_from_text(
                ocr_text=text,
                canonical_fields=canonical_fields,
                field_aliases=field_aliases_early,
                amount_labels=amount_label_cfg,
                pdf_config=pdf_table_cfg,
                page_texts=extraction.get("page_texts"),
            )
            if _ocr_fallback_fields:
                _sanitized = _repair_pre_extracted_fields(
                    _ocr_fallback_fields,
                    content=text,
                    format_hint=extraction.get("format", tipo_archivo),
                    prompt_config=prompt_config,
                    ocr_runtime=load_ocr_runtime_config(db),
                )
                _existing_fields = normalized_analysis.get("fields")
                if not isinstance(_existing_fields, dict):
                    _existing_fields = {}
                    normalized_analysis["fields"] = _existing_fields
                _text_fallback_changed = _merge_text_fallback_fields(_existing_fields, _sanitized)
                if _text_fallback_changed:
                    logger.info(
                        "text_fallback_rescue doc_id=%s fields=%s",
                        doc.id,
                        sorted(
                            k
                            for k in _sanitized
                            if k not in {"line_items", "line_item_page_groups"}
                        ),
                    )
        except Exception as _exc:
            logger.warning("text_fallback_rescue error (non-fatal): %s", _exc)

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

    # ── Escalación inline fast → deep ─────────────────────────────────────
    # Solo aplica cuando: (a) carril fast, (b) no cache, (c) doc de texto/PDF
    # (los estructurados usan _structured_direct_analysis, bypass sin HTTP, y
    # no se benefician de más timeout).
    _used_real_llm = (
        ai_enabled and not cached_analysis and not _skip_ai_for_structured and not has_structured
    )
    if ai_enabled and lane_decision.lane == "fast" and _used_real_llm:
        _current_analysis_path = str(analysis.get("analysis_path") or "")
        _sufficient, _escalation_reason = _fast_lane_result_is_sufficient(
            analysis_path=_current_analysis_path,
            tipo_doc=tipo_doc,
            confianza=confianza,
            classification_threshold=classification_threshold,
        )
        if not _sufficient:
            _t_deep = float(processing_cfg.get("lane_timeout_deep") or _LANE_TIMEOUTS["deep"])
            logger.info(
                "lane_escalation fast->deep doc_id=%s reason=%s timeout_deep=%.1fs",
                doc.id,
                _escalation_reason,
                _t_deep,
            )
            _escalation_started_at = time.perf_counter()
            _escalated_analysis = await analyze_document_fn(
                llm_content,
                filename,
                extraction.get("format", tipo_archivo),
                has_structured_rows=False,  # no bypass en escalación: forzar ruta LLM real
                recipe_config=_rc_for_run,
                structured_data=None,
                structured_metadata=None,
                image_bytes=bytes(vision_image_bytes) if vision_image_bytes else None,
                fallback_patterns=fallback_patterns,
                canonical_fields=canonical_fields,
                prompt_config=prompt_config,
                pre_extracted_fields=_pre_fields or None,
                reprocess_mode=reprocess_mode,
                bypass_cache=True,
                deep_reprocess_context=recipe_context.reprocess_context,
                deep_focus_fields=None,
                timeout_override=_t_deep,
                force_vision=bool(vision_image_bytes),
            )
            _set_stage_timing(stage_timings, "ai_escalation", _escalation_started_at)
            # Guard también para el resultado escalado
            _escalated_analysis = _guard_fallback_doc_type(_escalated_analysis, content=llm_content)
            _escalated_norm = _normalize_analysis_output(_escalated_analysis)
            _escalated_fields = _escalated_norm["fields"]
            if isinstance(_escalated_fields, dict) and _escalated_fields:
                # El resultado escalado tiene contenido: usarlo
                analysis = _escalated_analysis
                analysis.setdefault("analysis_path", "ok_llm_escalated")
                normalized_analysis = _escalated_norm
                tipo_doc = str(_escalated_norm["doc_type"])
                confianza = float(_escalated_norm["confidence"])
                razonamiento = str(_escalated_norm["reasoning"])
                analysis_fields = _escalated_fields
                requiere_revision = confianza < classification_threshold
                _lane_escalated = True
                _lane_escalation_reason = _escalation_reason
            else:
                logger.info(
                    "lane_escalation_noop doc_id=%s escalated_result_empty keeping_fast_result",
                    doc.id,
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

        structured_payload, recipe_name_detected = _build_structured_payload(
            structured_rows=structured_rows,
            structured_rows_all=structured_rows_all,
            sheet_profiles=sheet_profiles,
            sheet_metadata=sheet_metadata,
            sheet_used=sheet_used,
            sheet_names=sheet_names,
            headers_norm=headers_norm,
            headers_display=headers_display,
            recipe_name_detected=recipe_name_detected,
            recipe_name_field_candidates=recipe_name_field_candidates,
            structured_output_limit=structured_output_limit,
            filename=filename,
        )

        base_extracted = analysis_fields if isinstance(analysis_fields, dict) else {}
        datos_extraidos = _merge_structured_extraction(base_extracted, structured_payload)

        analysis_fields = datos_extraidos
        current_field_keys = _field_keys_for_reprocess(datos_extraidos)
        current_field_count = _count_detected_scalar_fields(datos_extraidos)

        logger.info(
            "structured_merge.run filename=%s base_keys=%s final_keys=%s line_items=%d total_filas=%d",
            filename,
            sorted(k for k in base_extracted.keys() if not str(k).startswith("_")),
            sorted(k for k in datos_extraidos.keys() if not str(k).startswith("_")),
            len(datos_extraidos.get("line_items") or []),
            int(datos_extraidos.get("total_filas") or 0),
        )

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

        if tipo_doc in ("STRUCTURED", "OTHER"):
            _inferred = _classify_structured_by_filename(
                filename, load_structured_filename_patterns(db)
            )
            if _inferred:
                tipo_doc = _inferred
                requiere_revision = True
                logger.info(
                    "structured_filename_classified filename=%s doc_type=%s",
                    filename,
                    tipo_doc,
                )
    else:
        datos_extraidos = analysis_fields or {}

    auto_recipe_created = local_auto_created
    auto_recipe_name: str | None = local_auto_name

    if (
        ai_enabled
        and not sheet_profiles
        and tipo_doc != "OTHER"
        and not recipe_context.explicit_recipe_context
    ):
        auto_recipe_started_at = time.perf_counter()
        auto_rc2, post_snap_id, auto_resolution_mode, auto_recipe_created, auto_recipe_name = (
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
            local_resolution = auto_resolution_mode or local_resolution
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
                    pre_extracted_fields=_pre_fields or None,
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
    # Normalizar a minúsculas y sin espacios para comparaciones deterministas.
    # Default "" (vacío) para no colisionar con ningún valor semántico real.
    _analysis_path = str(analysis.get("analysis_path") or "").strip().lower()

    # extraction_status semántico para observabilidad — basado en el camino real.
    _has_useful_data = isinstance(datos_extraidos, dict) and bool(datos_extraidos)
    if not isinstance(datos_extraidos, dict):
        _extraction_status = "failed"
    elif not datos_extraidos:
        _extraction_status = "partial_empty"
    elif _analysis_path in {
        "structured_direct",
        "ok_structured",
        "ok_snapshot_cache",
        "ok_pre_extract",
    }:
        _extraction_status = "ok_structured"
    elif _analysis_path in {"fallback", "fallback_error"}:
        _extraction_status = "ok_ocr_rescue" if _has_useful_data else "partial_timeout_fallback"
    elif _analysis_indicates_ai_failure(analysis, processing_cfg=processing_cfg):
        _extraction_status = "ok_ocr_rescue" if _has_useful_data else "partial_timeout_fallback"
    else:
        _extraction_status = "ok_llm"

    raw_ai_json = {
        "run": {
            "extraction_path": _analysis_path,
            "lane": {
                "lane": lane_decision.lane,
                "phase_timeout_secs": lane_decision.timeout_secs,
                "reasons": lane_decision.reasons,
                "force_vision": lane_decision.force_vision,
                "vision_first": lane_decision.vision_first,
                "ocr_quality_score": _ocr_quality_score,
                "escalated": _lane_escalated,
                "escalation_reason": _lane_escalation_reason,
            },
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
            "prompt": analysis.get("prompt_full", ""),
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
    error_detalle = None
    if isinstance(analysis, dict):
        _analysis_user_message = analysis.get("user_message")
        if isinstance(_analysis_user_message, str) and _analysis_user_message.strip():
            error_detalle = _analysis_user_message.strip()
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
            "error_detalle": error_detalle,
            "extraction_status": _extraction_status,
            "reprocess_status": "available",
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
        "importador.processing.completed doc_id=%s metrics=%s",
        doc.id,
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
