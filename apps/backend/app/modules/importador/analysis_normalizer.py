"""Helpers for normalizing importador analysis payloads."""

from __future__ import annotations


def _pick_analysis_value(analysis: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        value = analysis.get(key)
        if value is not None:
            return value
    return None


def _normalize_analysis_output(analysis: dict[str, object]) -> dict[str, object]:
    """Accept both the canonical English analyzer contract and legacy Spanish keys."""
    raw_doc_type = _pick_analysis_value(analysis, "doc_type", "tipo_documento")
    doc_type = str(raw_doc_type or "OTHER").strip().upper() or "OTHER"

    raw_confidence = _pick_analysis_value(analysis, "confidence", "confianza")
    try:
        confidence = float(raw_confidence if raw_confidence is not None else 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence > 1.0 and confidence <= 100.0:
        confidence = confidence / 100.0
    confidence = max(0.0, min(1.0, confidence))

    raw_reasoning = _pick_analysis_value(analysis, "reasoning", "razonamiento")
    reasoning = str(raw_reasoning or "").strip()

    raw_fields = _pick_analysis_value(analysis, "fields", "campos")
    fields = raw_fields if isinstance(raw_fields, dict) else {}

    return {
        "doc_type": doc_type,
        "confidence": confidence,
        "reasoning": reasoning,
        "fields": fields,
    }
