from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.importador import ImpRoutingSignal
from app.modules.importador.category_loader import get_doc_categories

from ..utils import json_safe as _json_safe
from .document_routing_admin_service import _document_canonical_payload as _canonical_document
from .document_routing_admin_service import _document_routing_source_data as _document_source_data
from .document_routing_agent import build_document_routing_decision


def record_routing_signal(
    db: Session,
    doc,
    *,
    user_id: str | None,
    event: str,
    changed_fields: list[str] | None = None,
    chosen_destination: str | None = None,
    payload: dict[str, Any] | None = None,
):
    decision = build_document_routing_decision(
        source_doc_type=getattr(doc, "tipo_documento_detectado", None),
        ai_confidence=getattr(doc, "confianza_clasificacion", None),
        extracted_data=_document_source_data(doc),
        canonical_document=_canonical_document(doc),
        category_keywords=get_doc_categories(db),
        requires_review=bool(getattr(doc, "requiere_revision", False)),
        db=db,
        tenant_id=getattr(doc, "tenant_id", None),
        destination_override=chosen_destination,
    )
    decision_payload = decision.model_dump(mode="json")
    signal_payload = {
        "event": event,
        "changed_fields": sorted(
            str(field) for field in (changed_fields or []) if str(field).strip()
        ),
        "chosen_destination": chosen_destination,
        "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "decision": decision_payload,
        "payload": _json_safe(payload or {}),
    }

    # REMOVIDO: routing_feedback en raw_ai_json era redundante con ImpRoutingSignal
    # (la tabla imp_routing_signal es la fuente de verdad y preserva el historial
    # completo; raw_ai_json solo guardaba el ultimo evento sobrescribiendo los
    # anteriores).

    row = ImpRoutingSignal(
        tenant_id=doc.tenant_id,
        documento_id=doc.id,
        event=event,
        user_id=str(user_id) if user_id else None,
        chosen_destination=chosen_destination,
        changed_fields=signal_payload["changed_fields"],
        routing_snapshot=decision_payload,
        payload=_json_safe(payload or {}),
    )
    db.add(row)
    db.flush()

    # REMOVIDO: log ROUTING_SIGNAL en imp_log_cambios era redundante con
    # ImpRoutingSignal. La tabla imp_routing_signal es la fuente de verdad
    # para senales de aprendizaje.
    return row
