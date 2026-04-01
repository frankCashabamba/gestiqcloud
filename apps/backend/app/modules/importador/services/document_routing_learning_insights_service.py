from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento, ImpRoutingProfile, ImpRoutingSignal
from app.modules.importador.runtime_config import load_learning_config
from app.modules.importador.schemas import (
    RoutingLearningInsightOut,
    RoutingProfileAdminIn,
    RoutingProfileUpdateProposalOut,
)

from ._routing_signals import document_type as _document_type
from ._routing_signals import event_weight as _event_weight
from ._routing_signals import normalize_text as _normalize_text
from ._routing_signals import source_doc_type as _source_doc_type
from .document_routing_admin_service import _serialize_profile


def _missing_fields(signal: ImpRoutingSignal) -> list[str]:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    raw = snapshot.get("missing_fields")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _confidence(signal: ImpRoutingSignal) -> float:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    try:
        value = float(snapshot.get("confidence") or 0.0)
    except (TypeError, ValueError):
        value = 0.0
    return max(0.0, min(1.0, value))


def _is_success_signal(signal: ImpRoutingSignal) -> bool:
    snapshot = signal.routing_snapshot if isinstance(signal.routing_snapshot, dict) else {}
    event = str(signal.event or "").strip().lower()
    return event in {"save", "confirm"} and bool(snapshot.get("required_fields_ok"))


def _iter_scalar_fields(doc: ImpDocumento) -> list[str]:
    confirmed = doc.datos_confirmados if isinstance(doc.datos_confirmados, dict) else {}
    fields: list[str] = []
    for key, value in confirmed.items():
        name = _normalize_text(key)
        if not name or name.startswith("_"):
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (dict, list, tuple, set)):
            continue
        fields.append(name)
    return fields


def list_routing_learning_insights(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    source_doc_type: str | None = None,
    document_type: str | None = None,
    limit: int = 20,
) -> list[RoutingLearningInsightOut]:
    rows = db.query(ImpRoutingSignal, ImpDocumento).join(
        ImpDocumento, ImpDocumento.id == ImpRoutingSignal.documento_id
    )
    if tenant_id is not None:
        rows = rows.filter(ImpRoutingSignal.tenant_id == tenant_id)
    joined = rows.order_by(ImpRoutingSignal.created_at.desc()).limit(max(limit * 20, 100)).all()

    wanted_source = str(source_doc_type or "").strip().upper()
    wanted_doc_type = str(document_type or "").strip().lower()

    weights = load_learning_config(db)
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "signals_count": 0,
            "save_count": 0,
            "confirm_count": 0,
            "edit_count": 0,
            "missing_counter": Counter(),
            "changed_counter": Counter(),
            "support_counter": Counter(),
            "success_confidence_weighted": 0.0,
            "success_weight_total": 0.0,
        }
    )

    for signal, doc in joined:
        group_source = _source_doc_type(signal, doc)
        group_document = _document_type(signal)
        if wanted_source and group_source != wanted_source:
            continue
        if wanted_doc_type and group_document != wanted_doc_type:
            continue

        bucket = grouped[(group_source, group_document)]
        bucket["signals_count"] += 1

        event = str(signal.event or "").strip().lower()
        if event == "save":
            bucket["save_count"] += 1
        elif event == "confirm":
            bucket["confirm_count"] += 1
        elif event == "edit":
            bucket["edit_count"] += 1

        weight = _event_weight(event, weights)
        for field in _missing_fields(signal):
            bucket["missing_counter"][field] += weight
        for field in signal.changed_fields or []:
            name = _normalize_text(field)
            if name:
                bucket["changed_counter"][name] += weight

        if _is_success_signal(signal):
            confidence = _confidence(signal)
            bucket["success_confidence_weighted"] += confidence * weight
            bucket["success_weight_total"] += weight
            for field in _iter_scalar_fields(doc):
                bucket["support_counter"][field] += weight

    insights: list[RoutingLearningInsightOut] = []
    for (group_source, group_document), data in grouped.items():
        if data["signals_count"] <= 0:
            continue
        missing_fields = [field for field, _ in data["missing_counter"].most_common(5)]
        changed_fields = [field for field, _ in data["changed_counter"].most_common(5)]
        required_groups = [[field] for field in missing_fields[:3]]
        support_fields = [
            field
            for field, _ in data["support_counter"].most_common(8)
            if field not in {item[0] for item in required_groups if item}
        ][:5]
        avg_success_confidence = (
            data["success_confidence_weighted"] / data["success_weight_total"]
            if data["success_weight_total"] > 0
            else 0.0
        )
        suggested_confidence_threshold = round(
            max(0.55, min(0.98, (avg_success_confidence or 0.8) - 0.03)),
            2,
        )
        notes: list[str] = []
        if missing_fields:
            notes.append(
                "Campos ausentes recurrentes detectados en señales de revisión o corrección."
            )
        if changed_fields:
            notes.append("Campos corregidos con frecuencia por usuarios en documentos similares.")
        if data["save_count"] > 0 or data["confirm_count"] > 0:
            notes.append("El umbral sugerido se calculó a partir de señales exitosas ponderadas.")

        insights.append(
            RoutingLearningInsightOut(
                source_doc_type=group_source,
                document_type=group_document,
                signals_count=data["signals_count"],
                save_count=data["save_count"],
                confirm_count=data["confirm_count"],
                edit_count=data["edit_count"],
                top_missing_fields=missing_fields,
                top_changed_fields=changed_fields,
                suggested_required_groups=required_groups,
                suggested_support_fields=support_fields,
                suggested_confidence_threshold=suggested_confidence_threshold,
                avg_success_confidence=round(avg_success_confidence, 2),
                notes=notes,
            )
        )

    insights.sort(key=lambda item: (-item.signals_count, item.source_doc_type, item.document_type))
    return insights[: max(1, min(limit, 50))]


def build_routing_profile_update_proposal(
    db: Session,
    *,
    profile_code: str,
    tenant_id: UUID | None = None,
    source_doc_type: str | None = None,
    document_type: str | None = None,
) -> RoutingProfileUpdateProposalOut:
    normalized_code = str(profile_code or "").strip().lower()
    profile = db.query(ImpRoutingProfile).filter(ImpRoutingProfile.code == normalized_code).first()
    if profile is None:
        raise ValueError("routing_profile_not_found")

    current_profile = _serialize_profile(profile)
    insights = list_routing_learning_insights(
        db,
        tenant_id=tenant_id,
        source_doc_type=source_doc_type,
        document_type=document_type or current_profile.document_type,
        limit=1,
    )
    if not insights:
        raise ValueError("routing_learning_insight_not_found")

    insight = insights[0]
    merged_required_groups = [list(group) for group in (current_profile.required_groups or [])]
    if insight.suggested_required_groups:
        merged_required_groups = [list(group) for group in insight.suggested_required_groups]

    required_seen = {
        field
        for group in merged_required_groups
        for field in group
        if isinstance(field, str) and field
    }
    for field in insight.top_changed_fields[:3]:
        if field and field not in required_seen:
            merged_required_groups.append([field])
            required_seen.add(field)

    merged_support_fields = list(
        dict.fromkeys(
            [
                *(current_profile.support_fields or []),
                *insight.suggested_support_fields,
                *insight.top_changed_fields[:3],
            ]
        )
    )

    merged_explanation_fields = list(
        dict.fromkeys(
            [
                *(current_profile.explanation_fields or []),
                *insight.top_changed_fields[:3],
                *insight.top_missing_fields[:2],
            ]
        )
    )

    proposed_update = RoutingProfileAdminIn(
        code=current_profile.code,
        document_type=current_profile.document_type,
        description=current_profile.description,
        suggested_destination=current_profile.suggested_destination,
        required_groups=merged_required_groups,
        support_fields=merged_support_fields[:8],
        explanation_fields=merged_explanation_fields[:8],
        blocked=current_profile.blocked,
        confidence_threshold=insight.suggested_confidence_threshold,
        active=current_profile.active,
    )
    return RoutingProfileUpdateProposalOut(
        profile_code=current_profile.code,
        current_profile=current_profile,
        proposed_update=proposed_update,
        based_on=insight,
    )
