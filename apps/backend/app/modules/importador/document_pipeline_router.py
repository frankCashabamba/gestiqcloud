from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .document_fields import safe_floatish


@dataclass(frozen=True, slots=True)
class ImportPipelineDecision:
    route: str
    family: str
    action: str
    confidence: float
    force_vision: bool = False
    vision_first: bool = False
    skip_ai: bool = False
    requires_review: bool = False
    reasons: tuple[str, ...] = ()
    user_message: str | None = None


def _norm(value: Any) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.lower()
    return " ".join(normalized.split())


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _text_stats(text: str) -> tuple[int, int]:
    raw = str(text or "").strip()
    words = re.findall(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]{2,}", raw)
    return len(raw), len(words)


def _field_evidence(pre_fields: dict[str, Any]) -> dict[str, Any]:
    line_items = pre_fields.get("line_items")
    has_line_items = isinstance(line_items, list) and any(
        isinstance(row, dict) for row in line_items
    )
    total_amount = safe_floatish(pre_fields.get("total_amount"))
    has_total = total_amount is not None and abs(float(total_amount)) > 0.0
    has_date = _nonempty(pre_fields.get("issue_date"))
    has_doc = _nonempty(pre_fields.get("doc_number"))
    has_vendor = _nonempty(pre_fields.get("vendor"))
    has_tax_id = _nonempty(pre_fields.get("vendor_tax_id"))
    strong_count = sum([has_total, has_date, has_doc, has_vendor, has_tax_id])
    return {
        "has_total": has_total,
        "has_date": has_date,
        "has_doc": has_doc,
        "has_vendor": has_vendor,
        "has_tax_id": has_tax_id,
        "has_line_items": has_line_items,
        "strong_count": strong_count,
        "has_primary": has_total or has_date or has_line_items,
    }


def classify_visual_family(text: str, *, doc_format: str, has_structured: bool) -> str:
    if has_structured:
        return "STRUCTURED"

    fmt = str(doc_format or "").upper()
    norm = _norm(text)
    if fmt in {"CSV", "JSON", "XML", "XML_UBL", "XML_FACTURAE", "XLS", "XLSX", "EXCEL"}:
        return "STRUCTURED"

    receipt_score = sum(
        1
        for marker in (
            "factura simplificada",
            "ticket",
            "tarjeta",
            "cambio",
            "total art",
            "art vendidos",
            "establecimiento",
            "numero operacion",
            "para el cliente",
        )
        if marker in norm
    )
    invoice_score = sum(
        1
        for marker in (
            "factura",
            "ruc",
            "datos del cliente",
            "razon social",
            "subtotal",
            "sub total",
            "valor total",
            "autorizacion",
            "codigo principal",
            "precio total",
        )
        if marker in norm
    )
    note_score = sum(
        1
        for marker in (
            "nota de venta",
            "cant",
            "descripcion",
            "v.unit",
            "v total",
            "f de pago",
        )
        if marker in norm
    )

    if receipt_score >= 2 and receipt_score >= invoice_score:
        return "THERMAL_RECEIPT"
    if invoice_score >= 3:
        return "PRINTED_INVOICE"
    if note_score >= 2:
        return "HANDWRITTEN_OR_LOW_STRUCTURE_NOTE"
    if fmt in {"IMAGE_OCR", "JPG", "JPEG", "PNG", "WEBP", "HEIC", "IMG"}:
        return "VISUAL_UNKNOWN"
    if fmt == "PDF_OCR":
        return "SCANNED_PDF"
    return "TEXT_UNKNOWN"


def decide_import_pipeline(
    *,
    doc_format: str,
    tipo_archivo: str,
    text: str,
    has_structured: bool,
    has_vision: bool,
    ocr_quality_score: float | None,
    pre_fields: dict[str, Any] | None,
    processing_cfg: dict[str, Any],
) -> ImportPipelineDecision:
    fields = dict(pre_fields or {})
    family = classify_visual_family(text, doc_format=doc_format, has_structured=has_structured)
    chars, words = _text_stats(text)
    evidence = _field_evidence(fields)
    fmt = str(doc_format or tipo_archivo or "").upper()
    visual = fmt in {"IMAGE_OCR", "PDF_OCR", "JPG", "JPEG", "PNG", "WEBP", "HEIC", "IMG"}

    quality = float(ocr_quality_score) if ocr_quality_score is not None else None
    reject_enabled = bool(processing_cfg.get("pipeline_reject_low_quality_enabled", True))
    reject_quality = float(processing_cfg.get("pipeline_reject_quality_threshold") or 0.50)
    reject_min_chars = int(processing_cfg.get("pipeline_reject_min_chars") or 180)
    reject_min_words = int(processing_cfg.get("pipeline_reject_min_words") or 45)
    vision_quality = float(processing_cfg.get("pipeline_vision_quality_threshold") or 0.68)
    min_local_strong = int(processing_cfg.get("pipeline_local_min_strong_fields") or 3)

    reasons: list[str] = [f"family={family}", f"chars={chars}", f"words={words}"]
    if quality is not None:
        reasons.append(f"ocr_quality={quality:.2f}")
    reasons.append(f"strong_fields={evidence['strong_count']}")

    if has_structured or family == "STRUCTURED":
        return ImportPipelineDecision(
            route="structured",
            family=family,
            action="LOCAL_STRUCTURED",
            confidence=0.9,
            reasons=tuple(reasons),
        )

    weak_text = chars < reject_min_chars or words < reject_min_words
    weak_quality = quality is None or quality < reject_quality
    no_primary_evidence = not bool(evidence["has_primary"])
    low_structure_family = family in {"HANDWRITTEN_OR_LOW_STRUCTURE_NOTE", "VISUAL_UNKNOWN"}

    if visual and reject_enabled and no_primary_evidence and weak_text and weak_quality:
        return ImportPipelineDecision(
            route="reject_low_quality",
            family=family,
            action="REJECT_LOW_QUALITY",
            confidence=0.2,
            skip_ai=True,
            requires_review=True,
            reasons=(*reasons, "weak_text", "weak_quality", "no_primary_evidence"),
            user_message=(
                "La imagen no tiene calidad suficiente para extraccion automatica fiable. "
                "Edita los datos manualmente o vuelve a subir una foto mas nitida y completa."
            ),
        )

    if visual and reject_enabled and no_primary_evidence and low_structure_family and weak_text:
        return ImportPipelineDecision(
            route="reject_low_structure",
            family=family,
            action="REJECT_LOW_QUALITY",
            confidence=0.25,
            skip_ai=True,
            requires_review=True,
            reasons=(*reasons, "low_structure", "no_primary_evidence"),
            user_message=(
                "El documento visual no aporta campos suficientes para automatizarlo con seguridad. "
                "Edita los datos manualmente o sube una imagen mas clara."
            ),
        )

    if (
        visual
        and reject_enabled
        and no_primary_evidence
        and int(evidence["strong_count"]) < min_local_strong
        and family not in {"PRINTED_INVOICE", "SCANNED_PDF"}
    ):
        return ImportPipelineDecision(
            route="reject_secondary_only",
            family=family,
            action="REJECT_LOW_QUALITY",
            confidence=0.3,
            skip_ai=True,
            requires_review=True,
            reasons=(*reasons, "secondary_fields_only", "no_primary_evidence"),
            user_message=(
                "El documento no tiene total, fecha ni lineas utilizables para extraerlo "
                "automaticamente con seguridad. Edita los datos manualmente o sube una imagen mejor."
            ),
        )

    if (
        family in {"PRINTED_INVOICE", "THERMAL_RECEIPT"}
        and int(evidence["strong_count"]) >= min_local_strong
    ):
        return ImportPipelineDecision(
            route="local_parser",
            family=family,
            action="LOCAL_PARSER",
            confidence=0.72,
            reasons=(*reasons, "local_evidence_sufficient"),
        )

    needs_vision = (
        bool(has_vision)
        and visual
        and (
            quality is None
            or quality < vision_quality
            or int(evidence["strong_count"]) < min_local_strong
            or not bool(evidence["has_total"])
        )
    )
    if needs_vision:
        return ImportPipelineDecision(
            route="vision_fallback",
            family=family,
            action="VISION_FALLBACK",
            confidence=0.55,
            force_vision=True,
            vision_first=quality is None or quality < reject_quality,
            reasons=(*reasons, "vision_available", "native_evidence_incomplete"),
        )

    return ImportPipelineDecision(
        route="text_or_default",
        family=family,
        action="TEXT_OR_DEFAULT",
        confidence=0.5,
        vision_first=False,
        reasons=tuple(reasons),
    )
