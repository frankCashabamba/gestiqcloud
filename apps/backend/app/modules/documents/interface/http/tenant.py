from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.documents.application.config import build_seller_info, load_tenant_doc_config
from app.modules.documents.application.orchestrator import DocumentOrchestrator
from app.modules.documents.application.repository import get_document, save_document
from app.modules.documents.application.template_engine import TemplateEngine
from app.modules.documents.domain.models import DocumentModel, SaleDraft, SellerInfo
from app.modules.shared.services.numbering import generar_numero_documento

router = APIRouter(
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


@router.post("/draft", response_model=DocumentModel)
def create_draft(payload: SaleDraft, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id_from_request(request)
    if tenant_id and payload.tenantId != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
    cfg = load_tenant_doc_config(db, payload.tenantId)
    seller_info = build_seller_info(db, payload.tenantId, cfg.branding)
    orchestrator = DocumentOrchestrator()
    try:
        return orchestrator.draft(payload, cfg, SellerInfo(**seller_info))
    except ValueError as exc:
        detail = exc.args[0] if exc.args else "validation_error"
        raise HTTPException(status_code=400, detail=detail)


@router.post("/issue", response_model=DocumentModel)
def issue_document(payload: SaleDraft, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id_from_request(request)
    if tenant_id and payload.tenantId != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
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
        detail = exc.args[0] if exc.args else "validation_error"
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


@documents_router.get("/{document_id}/render")
def render_document(document_id: str, request: Request, db: Session = Depends(get_db)):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    engine = TemplateEngine()
    return HTMLResponse(content=engine.render(doc))


@documents_router.get("/{document_id}/print")
def print_document(document_id: str, request: Request, db: Session = Depends(get_db)):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    engine = TemplateEngine()
    return HTMLResponse(content=engine.render(doc))
