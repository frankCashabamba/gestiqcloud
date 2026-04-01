from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

from .schemas import (
    CanonicalFieldOut,
    ColumnCandidateAssignIn,
    ColumnCandidateOut,
    FieldAliasCreateIn,
    FieldAliasOut,
    RoutingLearningInsightOut,
    RoutingPreviewDocumentOut,
    RoutingPreviewRequest,
    RoutingPreviewResponse,
    RoutingProfileAdminIn,
    RoutingProfileAdminOut,
    RoutingProfileUpdateProposalOut,
    RoutingRuleAdminIn,
    RoutingRuleAdminOut,
)
from .services.document_routing_admin_service import (
    create_routing_profile,
    create_routing_rule,
    delete_routing_profile,
    delete_routing_rule,
    list_preview_documents,
    list_routing_profiles,
    list_routing_rules,
    preview_routing_decision,
    update_routing_profile,
    update_routing_rule,
)
from .services.document_learning_queue_service import (
    flag_reprocess_candidates,
    list_reprocess_candidates,
)
from .services.document_routing_learning_insights_service import (
    build_routing_profile_update_proposal,
    list_routing_learning_insights,
)

router = APIRouter(
    prefix="/admin/importador/routing",
    tags=["admin:importador:routing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("/profiles", response_model=list[RoutingProfileAdminOut])
def get_routing_profiles(db: Session = Depends(get_db)):
    return list_routing_profiles(db)


@router.post("/profiles")
def post_routing_profile(payload: RoutingProfileAdminIn, db: Session = Depends(get_db)):
    return {"ok": True, "item": create_routing_profile(db, payload)}


@router.put("/profiles/{profile_code}")
def put_routing_profile(
    profile_code: str,
    payload: RoutingProfileAdminIn,
    db: Session = Depends(get_db),
):
    return {"ok": True, "item": update_routing_profile(db, profile_code, payload)}


@router.delete("/profiles/{profile_code}")
def remove_routing_profile(profile_code: str, db: Session = Depends(get_db)):
    return delete_routing_profile(db, profile_code)


@router.get("/rules", response_model=list[RoutingRuleAdminOut])
def get_routing_rules(
    scope_kind: str | None = Query(default=None, pattern="^(system|sector|tenant)$"),
    db: Session = Depends(get_db),
):
    return list_routing_rules(db, scope_kind=scope_kind)


@router.post("/rules")
def post_routing_rule(payload: RoutingRuleAdminIn, db: Session = Depends(get_db)):
    return {"ok": True, "item": create_routing_rule(db, payload)}


@router.put("/rules/{rule_id}")
def put_routing_rule(
    rule_id: UUID,
    payload: RoutingRuleAdminIn,
    db: Session = Depends(get_db),
):
    return {"ok": True, "item": update_routing_rule(db, rule_id, payload)}


@router.delete("/rules/{rule_id}")
def remove_routing_rule(rule_id: UUID, db: Session = Depends(get_db)):
    return delete_routing_rule(db, rule_id)


@router.post("/preview", response_model=RoutingPreviewResponse)
def post_routing_preview(payload: RoutingPreviewRequest, db: Session = Depends(get_db)):
    return preview_routing_decision(db, payload)


@router.get("/documents", response_model=list[RoutingPreviewDocumentOut])
def get_preview_documents(
    tenant_id: UUID,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=12, ge=1, le=25),
    db: Session = Depends(get_db),
):
    return list_preview_documents(db, tenant_id=tenant_id, q=q, limit=limit)


@router.get("/learning-insights", response_model=list[RoutingLearningInsightOut])
def get_routing_learning_insights(
    tenant_id: UUID | None = Query(default=None),
    source_doc_type: str | None = Query(default=None, max_length=80),
    document_type: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return list_routing_learning_insights(
        db,
        tenant_id=tenant_id,
        source_doc_type=source_doc_type,
        document_type=document_type,
        limit=limit,
    )


@router.get("/learning-insights/proposal", response_model=RoutingProfileUpdateProposalOut)
def get_routing_learning_proposal(
    profile_code: str = Query(min_length=2, max_length=80),
    tenant_id: UUID | None = Query(default=None),
    source_doc_type: str | None = Query(default=None, max_length=80),
    document_type: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
):
    try:
        return build_routing_profile_update_proposal(
            db,
            profile_code=profile_code,
            tenant_id=tenant_id,
            source_doc_type=source_doc_type,
            document_type=document_type,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "routing_profile_not_found":
            raise HTTPException(status_code=404, detail=detail)
        if detail == "routing_learning_insight_not_found":
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


# ── Learning Reprocess Queue ──────────────────────────────────────────────────

@router.get("/learning/reprocess-queue")
def get_reprocess_queue(
    tenant_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lista documentos confirmados cuyo snapshot aprendió cosas nuevas desde su procesamiento."""
    return {
        "items": list_reprocess_candidates(db, tenant_id=tenant_id, limit=limit),
    }


@router.post("/learning/reprocess-queue/flag")
def post_flag_reprocess_queue(
    tenant_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Marca como requiere_revision los documentos con aprendizaje pendiente de aplicar."""
    flagged = flag_reprocess_candidates(db, tenant_id=tenant_id, limit=limit)
    return {"ok": True, "flagged": flagged}


# ── Column Candidates ─────────────────────────────────────────────────────────

@router.get("/column-candidates", response_model=list[ColumnCandidateOut])
def get_column_candidates(
    unassigned_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from sqlalchemy import text as sa_text

    where = "WHERE canonical_field IS NULL" if unassigned_only else ""
    rows = db.execute(
        sa_text(
            f"SELECT id, alias, alias_norm, doc_type, tenant_id, seen_count, "  # noqa: S608
            f"       first_seen_at, last_seen_at, canonical_field, assigned_at, assigned_by "
            f"FROM imp_column_candidate {where} "
            f"ORDER BY seen_count DESC, last_seen_at DESC LIMIT :limit"
        ),
        {"limit": limit},
    ).fetchall()
    return [
        ColumnCandidateOut(
            id=row[0], alias=row[1], alias_norm=row[2], doc_type=row[3],
            tenant_id=row[4], seen_count=row[5], first_seen_at=row[6],
            last_seen_at=row[7], canonical_field=row[8],
            assigned_at=row[9], assigned_by=row[10],
        )
        for row in rows
    ]


@router.put("/column-candidates/{candidate_id}/assign")
def assign_column_candidate(
    candidate_id: UUID,
    payload: ColumnCandidateAssignIn,
    db: Session = Depends(get_db),
):
    """Asigna un campo canónico a un candidato y lo promueve a imp_field_alias."""
    from sqlalchemy import text as sa_text
    from .classifier_learning import _normalize_alias

    row = db.execute(
        sa_text("SELECT alias, alias_norm FROM imp_column_candidate WHERE id = :id"),
        {"id": str(candidate_id)},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="column_candidate_not_found")

    alias_norm = row[1] or _normalize_alias(row[0])

    # Actualizar el candidato
    db.execute(
        sa_text(
            "UPDATE imp_column_candidate "
            "SET canonical_field = :cf, assigned_at = now(), assigned_by = :by "
            "WHERE id = :id"
        ),
        {"cf": payload.canonical_field, "by": payload.assigned_by, "id": str(candidate_id)},
    )

    # Promover a imp_field_alias (global, source='learned')
    try:
        db.execute(
            sa_text(
                "INSERT INTO imp_field_alias "
                "    (tenant_id, canonical_field, alias, priority, source, confirmed_count, last_seen_at) "
                "VALUES (NULL, :cf, :alias, 5, 'learned', 1, now()) "
                "ON CONFLICT (canonical_field, alias) WHERE tenant_id IS NULL DO UPDATE "
                "    SET confirmed_count = imp_field_alias.confirmed_count + 1, last_seen_at = now()"
            ),
            {"cf": payload.canonical_field, "alias": alias_norm},
        )
    except Exception:
        pass  # Si ya existe el alias no es un error

    db.commit()
    from .field_alias_loader import invalidate_cache
    invalidate_cache()
    return {"ok": True}


@router.delete("/column-candidates/{candidate_id}")
def delete_column_candidate(candidate_id: UUID, db: Session = Depends(get_db)):
    from sqlalchemy import text as sa_text

    result = db.execute(
        sa_text("DELETE FROM imp_column_candidate WHERE id = :id"),
        {"id": str(candidate_id)},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="column_candidate_not_found")
    return {"ok": True}


# ── Field Aliases ─────────────────────────────────────────────────────────────

@router.get("/field-aliases", response_model=list[FieldAliasOut])
def get_field_aliases_admin(
    canonical_field: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
):
    from sqlalchemy import text as sa_text

    where = "WHERE active = TRUE"
    params: dict = {}
    if canonical_field:
        where += " AND canonical_field = :cf"
        params["cf"] = canonical_field

    rows = db.execute(
        sa_text(
            f"SELECT id, canonical_field, alias, tenant_id, active, priority, "  # noqa: S608
            f"       source, confirmed_count, last_seen_at "
            f"FROM imp_field_alias {where} "
            f"ORDER BY canonical_field, priority DESC, alias"
        ),
        params,
    ).fetchall()
    return [
        FieldAliasOut(
            id=row[0], canonical_field=row[1], alias=row[2], tenant_id=row[3],
            active=row[4], priority=row[5], source=row[6],
            confirmed_count=row[7], last_seen_at=row[8],
        )
        for row in rows
    ]


@router.post("/field-aliases")
def create_field_alias(payload: FieldAliasCreateIn, db: Session = Depends(get_db)):
    from sqlalchemy import text as sa_text
    from .classifier_learning import _normalize_alias, _is_safe_column_name

    if not _is_safe_column_name(payload.alias):
        raise HTTPException(status_code=422, detail="alias_unsafe")

    alias_norm = _normalize_alias(payload.alias)
    try:
        db.execute(
            sa_text(
                "INSERT INTO imp_field_alias "
                "    (tenant_id, canonical_field, alias, priority, source, confirmed_count) "
                "VALUES (:tid, :cf, :alias, :priority, 'manual', 0) "
                "ON CONFLICT (canonical_field, alias) WHERE tenant_id IS NULL DO UPDATE "
                "    SET priority = EXCLUDED.priority, active = TRUE"
            ),
            {
                "tid": str(payload.tenant_id) if payload.tenant_id else None,
                "cf": payload.canonical_field,
                "alias": alias_norm,
                "priority": payload.priority,
            },
        )
        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from .field_alias_loader import invalidate_cache
    invalidate_cache()
    return {"ok": True}


@router.delete("/field-aliases/{alias_id}")
def delete_field_alias(alias_id: UUID, db: Session = Depends(get_db)):
    from sqlalchemy import text as sa_text

    result = db.execute(
        sa_text("DELETE FROM imp_field_alias WHERE id = :id AND source != 'seed'"),
        {"id": str(alias_id)},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="alias_not_found_or_seed")

    from .field_alias_loader import invalidate_cache
    invalidate_cache()
    return {"ok": True}


# ── Canonical Fields ──────────────────────────────────────────────────────────

@router.get("/canonical-fields", response_model=list[CanonicalFieldOut])
def get_canonical_fields_admin(db: Session = Depends(get_db)):
    from sqlalchemy import text as sa_text

    rows = db.execute(
        sa_text(
            "SELECT name, field_type, projection_column FROM imp_canonical_field "
            "WHERE active = TRUE ORDER BY sort_order DESC, name"
        )
    ).fetchall()
    return [
        CanonicalFieldOut(name=row[0], field_type=row[1], projection_column=row[2])
        for row in rows
    ]
