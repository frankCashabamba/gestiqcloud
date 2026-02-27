from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.modelsimport import ImportMapping
from app.modules.imports.application.template_engine import (
    TemplateInterpreter,
    TemplateV2,
    validate_template,
)
from app.models.core.ui_field_config import TenantFieldConfig

logger = logging.getLogger("imports")

router = APIRouter(
    prefix="/templates",
    tags=["Import Templates V2"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_claims(request: Request) -> dict:
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        claims = with_access_claims(request)
    return claims


def _load_template_v2(data: dict[str, Any]) -> TemplateV2:
    errors = validate_template(data)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    return TemplateV2(**data)


# --------------- Schemas ---------------


class TemplateCreate(BaseModel):
    name: str
    source_type: str
    mappings: dict[str, Any]
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None
    dedupe_keys: list[str] | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    mappings: dict[str, Any] | None = None
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None
    dedupe_keys: list[str] | None = None


class SimulateRequest(BaseModel):
    sample_rows: list[dict[str, Any]]


# --------------- Endpoints ---------------


@router.get("/")
def list_templates(
    request: Request,
    source_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    q = db.query(ImportMapping).filter(ImportMapping.tenant_id == tenant_id)
    if source_type:
        q = q.filter(ImportMapping.source_type == source_type)
    return q.order_by(ImportMapping.created_at.desc()).all()


@router.get("/{template_id}")
def get_template(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    tpl = (
        db.query(ImportMapping)
        .filter(ImportMapping.id == template_id, ImportMapping.tenant_id == tenant_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.get("/fields")
def list_template_fields(
    request: Request,
    source_type: str | None = Query(None, description="products|expenses|invoices|bank|bank_transactions|recipes|generic"),
    db: Session = Depends(get_db),
):
    """
    Return canonical fields for a given source_type.
    Reads tenant_field_configs when available; falls back to defaults.
    """
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    fields: list[str] = []
    modules_to_try: list[str] = []
    if source_type:
        modules_to_try.extend(
            [
                f"imports_{source_type}",
                source_type,
            ]
        )

    # 1) Exact matches by module
    for mod in modules_to_try:
        rows = (
            db.query(TenantFieldConfig)
            .filter(TenantFieldConfig.tenant_id == tenant_id, TenantFieldConfig.module == mod)
            .order_by(TenantFieldConfig.created_at.asc())
            .all()
        )
        if rows:
            fields = [str(r.field) for r in rows if getattr(r, "field", None)]
            if fields:
                break

    # 2) Fallback: any module containing the source_type
    if not fields and source_type:
        rows = (
            db.query(TenantFieldConfig)
            .filter(
                TenantFieldConfig.tenant_id == tenant_id,
                TenantFieldConfig.module.ilike(f"%{source_type}%"),
            )
            .order_by(TenantFieldConfig.created_at.asc())
            .all()
        )
        if rows:
            fields = [str(r.field) for r in rows if getattr(r, "field", None)]

    # 3) Last resort: all fields for tenant (generic catch-all)
    if not fields:
        rows = (
            db.query(TenantFieldConfig)
            .filter(TenantFieldConfig.tenant_id == tenant_id)
            .order_by(TenantFieldConfig.created_at.asc())
            .all()
        )
        if rows:
            fields = [str(r.field) for r in rows if getattr(r, "field", None)]

    if not fields:
        raise HTTPException(status_code=404, detail="fields_not_configured")

    return {"source_type": source_type or "generic", "fields": fields}


@router.post("/", status_code=201)
def create_template(
    payload: TemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    # Validate mappings as TemplateV2 (backward compatible if client sends v2 schema)
    tpl_v2 = _load_template_v2(payload.mappings)

    tpl = ImportMapping(
        id=uuid4(),
        tenant_id=tenant_id,
        name=payload.name,
        source_type=payload.source_type,
        mappings=tpl_v2.model_dump(mode="json"),
        transforms=payload.transforms,
        defaults=payload.defaults,
        dedupe_keys=payload.dedupe_keys or tpl_v2.dedupe_keys,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.put("/{template_id}")
def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    tpl = (
        db.query(ImportMapping)
        .filter(ImportMapping.id == template_id, ImportMapping.tenant_id == tenant_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "mappings" in update_data and update_data["mappings"]:
        tpl_v2 = _load_template_v2(update_data["mappings"])
        update_data["mappings"] = tpl_v2.model_dump(mode="json")
        if not update_data.get("dedupe_keys") and tpl_v2.dedupe_keys:
            update_data["dedupe_keys"] = tpl_v2.dedupe_keys
    for field, value in update_data.items():
        setattr(tpl, field, value)

    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    tpl = (
        db.query(ImportMapping)
        .filter(ImportMapping.id == template_id, ImportMapping.tenant_id == tenant_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(tpl)
    db.commit()


@router.post("/{template_id}/simulate")
def simulate_template(
    template_id: UUID,
    payload: SimulateRequest,
    request: Request,
    db: Session = Depends(get_db),
):

    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    tpl = (
        db.query(ImportMapping)
        .filter(ImportMapping.id == template_id, ImportMapping.tenant_id == tenant_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    results: list[dict[str, Any]] = []
    mappings = tpl.mappings or {}
    try:
        tpl_v2 = _load_template_v2(mappings) if mappings else None
    except HTTPException:
        tpl_v2 = None

    if tpl_v2:
        interpreter = TemplateInterpreter(tpl_v2)
        # normalizar headers usando el diccionario de synonyms por idioma (best-effort)
        lang = (tpl_v2.match.language or ["es"])[0]
        for row in payload.sample_rows:
            headers_norm = list(row.keys())
            if headers_norm:
                try:
                    from app.modules.imports.application.template_engine.header_norm import normalize_headers
                except Exception:
                    headers_norm = list(row.keys())
                else:
                    headers_norm = normalize_headers(headers_norm, tpl_v2.header_normalization, lang)
            normalized_row = {h_norm: row.get(h_raw) for h_norm, h_raw in zip(headers_norm, row.keys())}
            results.extend(interpreter.process_rows([normalized_row]))
    else:
        from app.modules.imports.application.transform_dsl import apply_mapping_pipeline

        for row in payload.sample_rows:
            headers = list(row.keys())
            values = list(row.values())
            mapped = apply_mapping_pipeline(
                headers,
                values,
                mapping=tpl.mappings,
                transforms=tpl.transforms,
                defaults=tpl.defaults,
            )
            results.append(mapped)

    return {"template_id": str(template_id), "results": results}
