from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.modelsimport import ImportBatch, ImportItem, ImportMapping
from app.modules.imports.application.template_engine import (
    TemplateInterpreter,
    TemplateV2,
    validate_template,
    TemplateMatcher,
)
from app.modules.imports.application.template_engine.header_norm import normalize_headers

logger = logging.getLogger("imports")

router = APIRouter(
    prefix="/batches",
    tags=["Import Batches V2"],
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


def _parse_template_v2(data: dict[str, Any] | None) -> TemplateV2 | None:
    if not data:
        return None
    errors = validate_template(data)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    return TemplateV2(**data)


def _normalize_row_keys(row: dict[str, Any], tpl: TemplateV2, language: str) -> dict[str, Any]:
    """Normalize row headers with synonyms/accents."""
    if not row:
        return row
    headers_raw = list(row.keys())
    try:
        headers_norm = normalize_headers(headers_raw, tpl.header_normalization, language)
    except Exception:
        headers_norm = headers_raw
    normalized = {}
    for raw, norm in zip(headers_raw, headers_norm):
        normalized[norm] = row.get(raw)
    return normalized


def _file_path_from_key(file_key: str) -> str:
    if file_key.startswith("imports/"):
        return os.path.join("uploads", file_key.replace("/", os.sep))
    return file_key


# --------------- Schemas ---------------


class ApplyTemplateRequest(BaseModel):
    template_id: UUID | None = None
    template: dict[str, Any] | None = None


# --------------- Endpoints ---------------


@router.post("/{batch_id}/analyze")
def analyze_batch(
    batch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.services.excel_analyzer import analyze_excel_stream

    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    batch = (
        db.query(ImportBatch)
        .filter(ImportBatch.id == batch_id, ImportBatch.tenant_id == tenant_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Extract headers from the batch file
    headers: list[str] = []
    if batch.file_key:
        file_path = _file_path_from_key(batch.file_key)
        if os.path.exists(file_path):
            try:
                from io import BytesIO

                with open(file_path, "rb") as fh:
                    analysis = analyze_excel_stream(BytesIO(fh.read()))
                headers = [str(h) for h in (analysis.get("headers") or []) if str(h).strip()]
            except Exception:
                logger.warning("Failed to extract headers for batch %s", batch_id, exc_info=True)

    # Find best matching template (TemplateV2 aware)
    templates: list[ImportMapping] = (
        db.query(ImportMapping)
        .filter(ImportMapping.tenant_id == tenant_id)
        .order_by(ImportMapping.created_at.desc())
        .all()
    )

    tpl_pairs: list[tuple[ImportMapping, TemplateV2]] = []
    for tpl in templates:
        try:
            tv2 = _parse_template_v2(tpl.mappings or {})
        except HTTPException:
            tv2 = None
        if tv2:
            tpl_pairs.append((tpl, tv2))

    suggested = None
    if tpl_pairs:
        matcher = TemplateMatcher([p[1] for p in tpl_pairs])
        filename = batch.original_filename or ""
        language = "es"
        matched = matcher.match(filename, language)
        if matched:
            tpl_ref = next((tpl for tpl, tv2 in tpl_pairs if tv2 == matched), None)
            if tpl_ref:
                suggested = {"id": str(tpl_ref.id), "name": tpl_ref.name, "score": matched.match.priority / 100}

    # Fallback overlap score using headers if no match
    if not suggested:
        best_template = None
        best_score = 0.0
        for tpl in templates:
            mappings = tpl.mappings or {}
            if not mappings or not headers:
                continue
            header_set = {h.lower() for h in headers}
            key_set = {str(k).lower() for k in mappings.keys()}
            overlap = len(header_set & key_set)
            if overlap > 0:
                score = overlap / max(len(key_set), 1)
                if score > best_score:
                    best_score = score
                    best_template = tpl
        if best_template:
            suggested = {"id": str(best_template.id), "name": best_template.name, "score": best_score}

    return {
        "batch_id": str(batch_id),
        "headers": headers,
        "suggested_template": suggested,
    }


@router.post("/{batch_id}/apply-template")
def apply_template_to_batch(
    batch_id: UUID,
    payload: ApplyTemplateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")

    batch = (
        db.query(ImportBatch)
        .filter(ImportBatch.id == batch_id, ImportBatch.tenant_id == tenant_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Resolve template mappings
    tpl_v2: TemplateV2 | None = None
    mapping: dict[str, Any] | None = None
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None

    if payload.template_id:
        tpl = (
            db.query(ImportMapping)
            .filter(ImportMapping.id == payload.template_id, ImportMapping.tenant_id == tenant_id)
            .first()
        )
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        mapping = tpl.mappings
        transforms = tpl.transforms
        defaults = tpl.defaults
    elif payload.template:
        mapping = payload.template.get("mappings")
        transforms = payload.template.get("transforms")
        defaults = payload.template.get("defaults")
    else:
        raise HTTPException(status_code=422, detail="Provide template_id or template")

    try:
        tpl_v2 = _parse_template_v2(mapping if isinstance(mapping, dict) else None)
    except HTTPException:
        tpl_v2 = None

    items: list[ImportItem] = (
        db.query(ImportItem)
        .filter(ImportItem.batch_id == batch_id)
        .order_by(ImportItem.idx)
        .all()
    )

    processed = 0
    if tpl_v2:
        interpreter = TemplateInterpreter(tpl_v2)

        for item in items:
            raw = item.raw or {}
            language = raw.get("language") or (tpl_v2.match.language[0] if tpl_v2.match.language else "es")
            rows: list[dict[str, Any]] = []
            tables = raw.get("tables") or []
            if tables:
                for table in tables:
                    table_rows = table.get("rows") or []
                    for row in table_rows:
                        rows.append(_normalize_row_keys(row, tpl_v2, language))
            elif raw.get("kv"):
                rows.append(_normalize_row_keys(raw.get("kv"), tpl_v2, language))
            else:
                rows.append(_normalize_row_keys(raw, tpl_v2, language))

            processed_rows = interpreter.process_rows(rows)
            if not processed_rows:
                continue
            # Store dict when single row to keep legacy contract
            item.normalized = processed_rows[0] if len(processed_rows) == 1 else processed_rows
            processed += 1
    else:
        from app.modules.imports.application.transform_dsl import apply_mapping_pipeline

        for item in items:
            raw = item.raw or {}
            if not raw:
                continue
            headers = list(raw.keys())
            values = list(raw.values())
            mapped = apply_mapping_pipeline(
                headers,
                values,
                mapping=mapping,
                transforms=transforms,
                defaults=defaults,
            )
            item.normalized = mapped
            processed += 1

    db.commit()
    return {"batch_id": str(batch_id), "processed_items": processed}
