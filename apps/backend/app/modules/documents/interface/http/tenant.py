from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.modules.documents.application.config import build_seller_info, load_tenant_doc_config
from app.modules.documents.application.orchestrator import DocumentOrchestrator
from app.modules.documents.application.repository import get_document, save_document
from app.modules.documents.application.template_engine import TemplateEngine
from app.modules.documents.domain.models import DocumentModel, RenderFormat, SaleDraft, SellerInfo
from app.modules.shared.services.numbering import generar_numero_documento


def _resolve_tenant_currency(db: Session, tenant_id: str) -> str:
    try:
        tenant_uuid = UUID(str(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_tenant_id")

    row = db.execute(
        text(
            """
            SELECT COALESCE(
                NULLIF(UPPER(TRIM(cs.currency)), ''),
                NULLIF(UPPER(TRIM(cur.code)), '')
            )
            FROM company_settings cs
            LEFT JOIN currencies cur ON cur.id = cs.currency_id
            WHERE cs.tenant_id = :tid
            LIMIT 1
            """
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_uuid},
    ).first()
    if row:
        cur = row[0]
        if cur:
            cur = str(cur).strip().upper()
            if cur and len(cur) == 3 and cur.isalpha():
                return cur
    raise HTTPException(status_code=400, detail="currency_not_configured")


router = APIRouter(
    prefix="/documents/sales",
    tags=["Documents"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)

# Backward-compatible alias.
# NOTE: Marked deprecated at mount time (see app/platform/http/router.py).
legacy_router = APIRouter(
    prefix="/sales",
    tags=["Documents"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)

documents_router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_id_from_request(request: Request) -> str | None:
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        return None
    tid = claims.get("tenant_id")
    return str(tid) if tid is not None else None


def _create_draft(payload: SaleDraft, request: Request, db: Session = Depends(get_db)):
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _tenant_id_from_request(request)
    if tenant_id and payload.tenantId != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
    # Currency must come from DB settings (never from client).
    currency = _resolve_tenant_currency(db, payload.tenantId)
    payload = payload.model_copy(update={"currency": currency})
    cfg = load_tenant_doc_config(db, payload.tenantId)
    seller_info = build_seller_info(db, payload.tenantId, cfg.branding)
    orchestrator = DocumentOrchestrator()
    try:
        return orchestrator.draft(payload, cfg, SellerInfo(**seller_info))
    except ValueError as exc:
        detail = exc.args[0] if exc.args else "validation_error"
        raise HTTPException(status_code=400, detail=detail)


def _issue_document(payload: SaleDraft, request: Request, db: Session = Depends(get_db)):
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _tenant_id_from_request(request)
    if tenant_id and payload.tenantId != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
    # Currency must come from DB settings (never from client).
    currency = _resolve_tenant_currency(db, payload.tenantId)
    payload = payload.model_copy(update={"currency": currency})
    cfg = load_tenant_doc_config(db, payload.tenantId)
    seller_info = build_seller_info(db, payload.tenantId, cfg.branding)
    orchestrator = DocumentOrchestrator()
    numero = generar_numero_documento(db, payload.tenantId, "pos_receipt")
    parts = str(numero).split("-")
    series = "-".join(parts[:2]) if len(parts) >= 2 else None
    sequential = parts[-1] if parts else None
    try:
        doc = orchestrator.issue(
            payload,
            cfg,
            SellerInfo(**seller_info),
            series=series,
            sequential=sequential,
        )
    except ValueError as exc:
        # Pydantic ValidationError inherits ValueError; prefer structured errors if available.
        if hasattr(exc, "errors") and callable(getattr(exc, "errors")):  # type: ignore[attr-defined]
            try:
                detail = exc.errors()  # type: ignore[attr-defined]
            except Exception:
                detail = str(exc) or "validation_error"
        else:
            detail = exc.args[0] if exc.args else (str(exc) or "validation_error")
        raise HTTPException(status_code=400, detail=detail)
    save_document(
        db,
        tenant_id=payload.tenantId,
        doc=doc,
        config_version=cfg.config_version,
        effective_from=cfg.effective_from,
        country_pack_version=orchestrator.country_pack.version,
    )
    return doc


# Register routes on both the new router and the legacy alias.
router.add_api_route("/draft", _create_draft, methods=["POST"], response_model=DocumentModel)
router.add_api_route("/issue", _issue_document, methods=["POST"], response_model=DocumentModel)
legacy_router.add_api_route("/draft", _create_draft, methods=["POST"], response_model=DocumentModel)
legacy_router.add_api_route(
    "/issue", _issue_document, methods=["POST"], response_model=DocumentModel
)


@documents_router.get("/{document_id}/render")
def render_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    format: RenderFormat | None = Query(default=None),  # noqa: A002
):
    ensure_guc_from_request(request, db, persist=True)
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    if format:
        doc = doc.model_copy(deep=True)
        doc.render.format = format  # type: ignore[assignment]
    engine = TemplateEngine()
    return HTMLResponse(content=engine.render(doc))


@documents_router.get("/{document_id}/print")
def print_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    format: RenderFormat | None = Query(default=None),  # noqa: A002
):
    ensure_guc_from_request(request, db, persist=True)
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    if format:
        doc = doc.model_copy(deep=True)
        doc.render.format = format  # type: ignore[assignment]
    engine = TemplateEngine()
    return HTMLResponse(content=engine.render(doc))
