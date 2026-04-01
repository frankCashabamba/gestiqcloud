"""Helpers compartidos para procesamiento de señales de routing.

Usado por document_model_learning_service y document_routing_learning_insights_service.
"""

from __future__ import annotations

from typing import Any

from app.models.importador import ImpDocumento, ImpRoutingSignal


def normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def is_scalar(value: Any) -> bool:
    return value is not None and not isinstance(value, (dict, list, tuple, set, bool))


def event_weight(event: str, weights: dict | None = None) -> float:
    w = weights or {}
    normalized = str(event or "").strip().lower()
    if normalized == "save":
        return float(w.get("event_weight_save", 4.0))
    if normalized == "confirm":
        return float(w.get("event_weight_confirm", 3.0))
    if normalized == "edit":
        return float(w.get("event_weight_edit", 1.35))
    return float(w.get("event_weight_default", 1.0))


def source_doc_type(signal: ImpRoutingSignal, doc: ImpDocumento) -> str:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    raw = (
        snapshot.get("source_doc_type") or getattr(doc, "tipo_documento_detectado", None) or "OTHER"
    )
    return str(raw).strip().upper() or "OTHER"


def document_type(signal: ImpRoutingSignal) -> str:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    raw = snapshot.get("document_type") or signal.chosen_destination or "other"
    return str(raw).strip().lower() or "other"
