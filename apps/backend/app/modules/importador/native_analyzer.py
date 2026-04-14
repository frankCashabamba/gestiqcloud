"""Analizador determinista para el importador.

Esta capa no usa proveedores IA. Solo aplica extracción nativa sobre texto OCR
ya obtenido por el pipeline de librerías locales.
"""

from __future__ import annotations

from typing import Any

from .document_fields import detect_document_total
from .text_fallback_extractor import extract_fields_from_text


def _merge_fields(*parts: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for part in parts:
        if isinstance(part, dict):
            for key, value in part.items():
                if value not in (None, "", [], {}) and key not in merged:
                    merged[key] = value
    return merged


async def analyze_document(
    content: str,
    filename: str,
    format_hint: str,
    *,
    has_structured_rows: bool = False,
    recipe_config: dict[str, Any] | None = None,
    structured_data: list[dict[str, Any]] | None = None,
    structured_metadata: dict[str, Any] | None = None,
    image_bytes: bytes | None = None,
    fallback_patterns: dict[str, Any] | None = None,
    canonical_fields: dict[str, dict] | None = None,
    prompt_config: dict[str, Any] | None = None,
    pre_extracted_fields: dict[str, Any] | None = None,
    reprocess_mode: str = "fast",
    bypass_cache: bool = False,
    deep_reprocess_context: dict[str, Any] | None = None,
    deep_focus_fields: list[str] | None = None,
    timeout_override: float | None = None,
    force_vision: bool = False,
    field_aliases: dict[str, list[str]] | None = None,
    amount_labels: dict[str, list[str]] | None = None,
    pdf_config: dict[str, Any] | None = None,
    page_texts: list[str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Return a deterministic extraction result without calling IA."""
    del filename, format_hint, recipe_config, structured_data, structured_metadata
    del image_bytes, fallback_patterns, reprocess_mode, bypass_cache
    del deep_reprocess_context, deep_focus_fields, timeout_override, force_vision

    field_aliases = field_aliases or {}
    amount_labels = amount_labels or {}
    if not amount_labels and isinstance(prompt_config, dict):
        maybe_amounts = prompt_config.get("amount_labels")
        if isinstance(maybe_amounts, dict):
            amount_labels = {
                str(key): list(value)
                for key, value in maybe_amounts.items()
                if isinstance(value, list)
            }

    extracted = extract_fields_from_text(
        content or "",
        canonical_fields or {},
        field_aliases,
        amount_labels,
        pdf_config=pdf_config,
        page_texts=page_texts,
    )

    fields = _merge_fields(pre_extracted_fields, extracted)
    if "line_items" in fields and "total_amount" not in fields:
        derived_total = detect_document_total(fields)
        if derived_total is not None:
            fields["total_amount"] = derived_total

    confidence = 0.25
    field_count = len(
        [key for key, value in fields.items() if value not in (None, "", [], {})]
    )
    if field_count:
        confidence = min(0.95, 0.35 + (field_count * 0.08))

    return {
        "doc_type": "OTHER",
        "confidence": confidence,
        "reasoning": "Native deterministic extraction only.",
        "fields": fields,
        "raw_response": "reason=native_deterministic",
        "model_used": "native-deterministic",
        "analysis_path": "ok_native",
        "requires_review": confidence < 0.5,
    }
