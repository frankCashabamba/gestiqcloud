from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento, ImpRoutingProfile, ImpRoutingRule
from app.modules.importador.category_loader import get_doc_categories
from app.services.field_config import resolve_sector_code

from ..schemas import (
    RoutingPreviewDocumentOut,
    RoutingPreviewRequest,
    RoutingPreviewResponse,
    RoutingProfileAdminIn,
    RoutingProfileAdminOut,
    RoutingRuleAdminIn,
    RoutingRuleAdminOut,
)
from .document_routing_agent import (
    build_document_routing_decision,
    invalidate_document_routing_cache,
    resolve_routing_profile_match,
)


def _normalize_profile_code(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_source_key(value: str) -> str:
    return str(value or "").strip().upper()


def _serialize_profile(row: ImpRoutingProfile) -> RoutingProfileAdminOut:
    return RoutingProfileAdminOut(
        id=row.id,
        code=row.code,
        document_type=row.document_type,
        description=row.description,
        suggested_destination=row.suggested_destination,
        required_groups=row.required_groups or [],
        support_fields=row.support_fields or [],
        explanation_fields=row.explanation_fields or [],
        blocked=bool(row.blocked),
        confidence_threshold=float(row.confidence_threshold),
        active=bool(row.active),
    )


def _rule_scope_kind(row: ImpRoutingRule) -> str:
    if row.tenant_id:
        return "tenant"
    if str(row.sector or "").strip().lower() == "_system":
        return "system"
    return "sector"


def _serialize_rule(row: ImpRoutingRule) -> RoutingRuleAdminOut:
    return RoutingRuleAdminOut(
        id=row.id,
        scope_kind=_rule_scope_kind(row),
        tenant_id=row.tenant_id,
        sector=None if _rule_scope_kind(row) == "system" else row.sector,
        source_kind=row.source_kind,
        source_key=row.source_key,
        profile_code=row.profile_code,
        priority=row.priority,
        active=bool(row.active),
    )


def _serialize_preview_document(row: ImpDocumento) -> RoutingPreviewDocumentOut:
    return RoutingPreviewDocumentOut(
        id=row.id,
        tenant_id=row.tenant_id,
        nombre_archivo=row.nombre_archivo,
        tipo_documento_detectado=row.tipo_documento_detectado,
        estado=row.estado,
        created_at=row.created_at,
        proveedor_detectado=row.proveedor_detectado,
        monto_total=row.monto_total,
    )


def _document_routing_source_data(doc: ImpDocumento) -> dict:
    raw = doc.datos_confirmados or doc.datos_extraidos or {}
    data = dict(raw) if isinstance(raw, dict) else {}
    if "vendor" not in data and getattr(doc, "proveedor_detectado", None):
        data["vendor"] = doc.proveedor_detectado
    if "vendor_tax_id" not in data and getattr(doc, "ruc_detectado", None):
        data["vendor_tax_id"] = doc.ruc_detectado
    if "total_amount" not in data and getattr(doc, "monto_total", None) is not None:
        data["total_amount"] = doc.monto_total
    if "issue_date" not in data and getattr(doc, "fecha_documento", None):
        data["issue_date"] = doc.fecha_documento
    if "currency" not in data and getattr(doc, "moneda", None):
        data["currency"] = doc.moneda
    return data


def _document_canonical_payload(doc: ImpDocumento) -> dict:
    raw_ai_json = doc.raw_ai_json if isinstance(doc.raw_ai_json, dict) else {}
    canonical_document = raw_ai_json.get("canonical_document")
    return canonical_document if isinstance(canonical_document, dict) else {}


def _resolve_rule_scope(db: Session, payload: RoutingRuleAdminIn) -> tuple[UUID | None, str | None]:
    if payload.scope_kind == "tenant":
        if payload.tenant_id is None:
            raise HTTPException(status_code=400, detail="tenant_id_required")
        return payload.tenant_id, None
    if payload.scope_kind == "sector":
        if not str(payload.sector or "").strip():
            raise HTTPException(status_code=400, detail="sector_required")
        return None, resolve_sector_code(db, payload.sector)
    return None, "_system"


def _ensure_profile_exists(db: Session, profile_code: str) -> ImpRoutingProfile:
    profile = (
        db.query(ImpRoutingProfile)
        .filter(ImpRoutingProfile.code == _normalize_profile_code(profile_code))
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="routing_profile_not_found")
    return profile


def _find_rule_conflict(
    db: Session,
    *,
    tenant_id: UUID | None,
    sector: str | None,
    source_kind: str,
    source_key: str,
    exclude_id: UUID | None = None,
) -> ImpRoutingRule | None:
    query = db.query(ImpRoutingRule).filter(
        ImpRoutingRule.source_kind == source_kind,
        ImpRoutingRule.source_key == source_key,
    )
    if tenant_id is not None:
        query = query.filter(ImpRoutingRule.tenant_id == tenant_id)
    else:
        query = query.filter(ImpRoutingRule.tenant_id.is_(None), ImpRoutingRule.sector == sector)
    if exclude_id is not None:
        query = query.filter(ImpRoutingRule.id != exclude_id)
    return query.first()


def list_routing_profiles(db: Session) -> list[RoutingProfileAdminOut]:
    rows = db.query(ImpRoutingProfile).order_by(ImpRoutingProfile.code.asc()).all()
    return [_serialize_profile(row) for row in rows]


def create_routing_profile(db: Session, payload: RoutingProfileAdminIn) -> RoutingProfileAdminOut:
    code = _normalize_profile_code(payload.code)
    exists = db.query(ImpRoutingProfile).filter(ImpRoutingProfile.code == code).first()
    if exists:
        raise HTTPException(status_code=400, detail="routing_profile_code_exists")

    row = ImpRoutingProfile(
        code=code,
        document_type=str(payload.document_type).strip(),
        description=payload.description,
        suggested_destination=payload.suggested_destination,
        required_groups=payload.required_groups,
        support_fields=payload.support_fields,
        explanation_fields=payload.explanation_fields,
        blocked=payload.blocked,
        confidence_threshold=payload.confidence_threshold,
        active=payload.active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    invalidate_document_routing_cache()
    return _serialize_profile(row)


def update_routing_profile(
    db: Session, profile_code: str, payload: RoutingProfileAdminIn
) -> RoutingProfileAdminOut:
    current_code = _normalize_profile_code(profile_code)
    row = db.query(ImpRoutingProfile).filter(ImpRoutingProfile.code == current_code).first()
    if not row:
        raise HTTPException(status_code=404, detail="routing_profile_not_found")

    new_code = _normalize_profile_code(payload.code)
    if new_code != current_code:
        exists = db.query(ImpRoutingProfile).filter(ImpRoutingProfile.code == new_code).first()
        if exists:
            raise HTTPException(status_code=400, detail="routing_profile_code_exists")
        db.query(ImpRoutingRule).filter(ImpRoutingRule.profile_code == current_code).update(
            {"profile_code": new_code}
        )
        row.code = new_code

    row.document_type = str(payload.document_type).strip()
    row.description = payload.description
    row.suggested_destination = payload.suggested_destination
    row.required_groups = payload.required_groups
    row.support_fields = payload.support_fields
    row.explanation_fields = payload.explanation_fields
    row.blocked = payload.blocked
    row.confidence_threshold = payload.confidence_threshold
    row.active = payload.active
    db.commit()
    db.refresh(row)
    invalidate_document_routing_cache()
    return _serialize_profile(row)


def delete_routing_profile(db: Session, profile_code: str) -> dict[str, bool]:
    row = (
        db.query(ImpRoutingProfile)
        .filter(ImpRoutingProfile.code == _normalize_profile_code(profile_code))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="routing_profile_not_found")

    linked_rules = db.query(ImpRoutingRule).filter(ImpRoutingRule.profile_code == row.code).count()
    if linked_rules:
        raise HTTPException(status_code=409, detail="routing_profile_has_rules")

    db.delete(row)
    db.commit()
    invalidate_document_routing_cache()
    return {"ok": True}


def list_routing_rules(
    db: Session,
    *,
    scope_kind: str | None = None,
) -> list[RoutingRuleAdminOut]:
    query = db.query(ImpRoutingRule)
    if scope_kind == "tenant":
        query = query.filter(ImpRoutingRule.tenant_id.isnot(None))
    elif scope_kind == "sector":
        query = query.filter(ImpRoutingRule.tenant_id.is_(None), ImpRoutingRule.sector != "_system")
    elif scope_kind == "system":
        query = query.filter(ImpRoutingRule.tenant_id.is_(None), ImpRoutingRule.sector == "_system")

    rows = query.order_by(
        ImpRoutingRule.source_kind.asc(),
        ImpRoutingRule.source_key.asc(),
        ImpRoutingRule.priority.asc(),
    ).all()
    return [_serialize_rule(row) for row in rows]


def list_preview_documents(
    db: Session,
    *,
    tenant_id: UUID,
    q: str | None = None,
    limit: int = 12,
) -> list[RoutingPreviewDocumentOut]:
    query = db.query(ImpDocumento).filter(ImpDocumento.tenant_id == tenant_id)
    search = str(q or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                ImpDocumento.nombre_archivo.ilike(like),
                ImpDocumento.tipo_documento_detectado.ilike(like),
                ImpDocumento.proveedor_detectado.ilike(like),
            )
        )
    rows = (
        query.order_by(ImpDocumento.created_at.desc())
        .limit(max(1, min(int(limit or 12), 25)))
        .all()
    )
    return [_serialize_preview_document(row) for row in rows]


def create_routing_rule(db: Session, payload: RoutingRuleAdminIn) -> RoutingRuleAdminOut:
    _ensure_profile_exists(db, payload.profile_code)
    tenant_id, sector = _resolve_rule_scope(db, payload)
    source_key = _normalize_source_key(payload.source_key)

    conflict = _find_rule_conflict(
        db,
        tenant_id=tenant_id,
        sector=sector,
        source_kind=payload.source_kind,
        source_key=source_key,
    )
    if conflict:
        raise HTTPException(status_code=400, detail="routing_rule_scope_conflict")

    row = ImpRoutingRule(
        tenant_id=tenant_id,
        sector=sector,
        source_kind=payload.source_kind,
        source_key=source_key,
        profile_code=_normalize_profile_code(payload.profile_code),
        priority=payload.priority,
        active=payload.active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    invalidate_document_routing_cache()
    return _serialize_rule(row)


def update_routing_rule(
    db: Session, rule_id: UUID, payload: RoutingRuleAdminIn
) -> RoutingRuleAdminOut:
    row = db.query(ImpRoutingRule).filter(ImpRoutingRule.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="routing_rule_not_found")

    _ensure_profile_exists(db, payload.profile_code)
    tenant_id, sector = _resolve_rule_scope(db, payload)
    source_key = _normalize_source_key(payload.source_key)

    conflict = _find_rule_conflict(
        db,
        tenant_id=tenant_id,
        sector=sector,
        source_kind=payload.source_kind,
        source_key=source_key,
        exclude_id=rule_id,
    )
    if conflict:
        raise HTTPException(status_code=400, detail="routing_rule_scope_conflict")

    row.tenant_id = tenant_id
    row.sector = sector
    row.source_kind = payload.source_kind
    row.source_key = source_key
    row.profile_code = _normalize_profile_code(payload.profile_code)
    row.priority = payload.priority
    row.active = payload.active
    db.commit()
    db.refresh(row)
    invalidate_document_routing_cache()
    return _serialize_rule(row)


def delete_routing_rule(db: Session, rule_id: UUID) -> dict[str, bool]:
    row = db.query(ImpRoutingRule).filter(ImpRoutingRule.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="routing_rule_not_found")
    db.delete(row)
    db.commit()
    invalidate_document_routing_cache()
    return {"ok": True}


def preview_routing_decision(db: Session, payload: RoutingPreviewRequest) -> RoutingPreviewResponse:
    tenant_id: UUID | None = None
    sector_override: str | None = None
    doc: ImpDocumento | None = None
    if payload.document_id is not None:
        doc = db.query(ImpDocumento).filter(ImpDocumento.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="routing_preview_document_not_found")
    if payload.scope_kind == "tenant":
        tenant_id = payload.tenant_id or (doc.tenant_id if doc is not None else None)
        if tenant_id is None:
            raise HTTPException(status_code=400, detail="tenant_id_required")
        if (
            doc is not None
            and payload.tenant_id is not None
            and str(payload.tenant_id) != str(doc.tenant_id)
        ):
            raise HTTPException(status_code=400, detail="routing_preview_document_tenant_mismatch")
    elif payload.scope_kind == "sector":
        if not str(payload.sector or "").strip():
            raise HTTPException(status_code=400, detail="sector_required")
        sector_override = payload.sector

    if doc is not None:
        canonical_document = _document_canonical_payload(doc)
        extracted_data = _document_routing_source_data(doc)
        source_doc_type = doc.tipo_documento_detectado
        ai_confidence = doc.confianza_clasificacion
        requires_review = bool(doc.requiere_revision) or payload.requires_review
        source_category_override = payload.source_category
    else:
        canonical_fields = (
            payload.canonical_fields if isinstance(payload.canonical_fields, dict) else {}
        )
        canonical_document = {"fields": canonical_fields}
        extracted_data = payload.extracted_data if isinstance(payload.extracted_data, dict) else {}
        source_doc_type = payload.source_doc_type
        ai_confidence = payload.ai_confidence
        requires_review = payload.requires_review
        source_category_override = payload.source_category

    decision = build_document_routing_decision(
        source_doc_type=source_doc_type,
        source_category_override=source_category_override,
        ai_confidence=ai_confidence,
        extracted_data=extracted_data,
        canonical_document=canonical_document,
        category_keywords=get_doc_categories(db),
        requires_review=requires_review,
        destination_override=payload.destination_override,
        db=db,
        tenant_id=tenant_id,
        sector_override=sector_override,
    )
    resolution = resolve_routing_profile_match(
        db=db,
        tenant_id=tenant_id,
        sector_override=sector_override,
        source_doc_type=payload.source_doc_type,
        source_category=decision.source_category,
        destination_override=payload.destination_override,
    )
    return RoutingPreviewResponse(
        decision=decision,
        profile_code=resolution.profile.code,
        matched_by=resolution.matched_by,
        matched_scope=resolution.matched_scope,
        rule_source_kind=resolution.rule_source_kind,
        rule_source_key=resolution.rule_source_key,
        resolved_sector=resolution.resolved_sector,
        document_id=(doc.id if doc is not None else payload.document_id),
        document_name=(doc.nombre_archivo if doc is not None else None),
        tenant_id=(doc.tenant_id if doc is not None else tenant_id),
    )
