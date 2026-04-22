from __future__ import annotations

import os
from datetime import UTC
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.audit_events import audit_event
from app.core.authz import require_scope
from app.core.dependencies import get_tenant_uuid
from app.db.rls import ensure_rls
from app.models.core.document import Document
from app.models.core.facturacion import Invoice
from app.modules.invoicing import schemas
from app.modules.invoicing.crud import factura_crud

router = APIRouter(
    prefix="/invoicing",
    tags=["Invoicing"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("")
def list_invoices(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    q: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    from datetime import datetime

    tenant_id = get_tenant_uuid(request)

    # ── 1. Facturas del módulo clásico (Invoice) ──────────────────────────────
    old_invoices = factura_crud.list_primary_invoices(
        db=db, tenant_id=tenant_id, status=status, query=q, date_from=date_from, date_to=date_to
    )

    def _iso(d) -> str | None:
        if d is None:
            return None
        if isinstance(d, str):
            return d
        if hasattr(d, "isoformat"):
            return d.isoformat()
        return str(d)

    result: list[dict] = []
    for inv in old_invoices:
        result.append(
            {
                "id": str(inv.id),
                "number": inv.number,
                "issue_date": _iso(inv.issue_date),
                "status": inv.status,
                "subtotal": float(inv.subtotal) if inv.subtotal is not None else None,
                "tax": float(inv.vat) if inv.vat is not None else None,
                "total": (
                    float(inv.total)
                    if inv.total is not None
                    else (float(inv.amount) if getattr(inv, "amount", None) is not None else None)
                ),
                "customer_name": inv.customer.name if inv.customer else None,
                "source": "invoice",
                "_sort_key": inv.issue_date,
            }
        )

    # ── 2. Documentos del módulo POS (Document con doc_type=FACTURA) ──────────
    doc_q = db.query(Document).filter(
        Document.tenant_id == tenant_id,
        Document.doc_type == "FACTURA",
    )

    if status:
        doc_q = doc_q.filter(Document.status == status.upper())
    if date_from:
        try:
            doc_q = doc_q.filter(
                Document.issued_at >= datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC)
            )
        except ValueError:
            pass
    if date_to:
        try:
            doc_q = doc_q.filter(
                Document.issued_at <= datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=UTC)
            )
        except ValueError:
            pass

    for doc in doc_q.all():
        payload = doc.payload or {}
        totals = payload.get("totals") or {}
        buyer = payload.get("buyer") or {}
        doc_info = payload.get("document") or {}
        series = doc.series or doc_info.get("series", "")
        sequential = doc.sequential or doc_info.get("sequential", "")
        numero = (
            f"{series}-{sequential}"
            if series and sequential
            else (series or sequential or str(doc.id)[:8])
        )
        buyer_name = buyer.get("name") or buyer.get("businessName") or ""
        buyer_id = buyer.get("idNumber", "")
        # Filtro de búsqueda sobre documentos
        if q:
            qlow = q.lower()
            if not any(qlow in s.lower() for s in [numero, buyer_name, buyer_id] if s):
                continue
        result.append(
            {
                "id": str(doc.id),
                "number": numero,
                "issue_date": _iso(doc.issued_at),
                "date": _iso(doc.issued_at),
                "status": doc.status.lower(),
                "subtotal": (
                    float(totals["subtotal"]) if totals.get("subtotal") is not None else None
                ),
                "tax": float(totals["taxTotal"]) if totals.get("taxTotal") is not None else None,
                "total": (
                    float(totals["grandTotal"]) if totals.get("grandTotal") is not None else None
                ),
                "customer_name": buyer_name,
                "buyer_id": buyer_id,
                "source": "document",
                "_sort_key": doc.issued_at,
            }
        )

    # ── 3. Ordenar por fecha descendente ─────────────────────────────────────
    def _sort_key(item):
        from datetime import date as date_type

        k = item.get("_sort_key")
        if k is None:
            return datetime.min.replace(tzinfo=UTC)
        if isinstance(k, str):
            try:
                dt = datetime.fromisoformat(k)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:
                return datetime.min.replace(tzinfo=UTC)
        if isinstance(k, datetime):
            if k.tzinfo is None:
                return k.replace(tzinfo=UTC)
            return k
        if isinstance(k, date_type):
            return datetime(k.year, k.month, k.day, tzinfo=UTC)
        return datetime.min.replace(tzinfo=UTC)

    result.sort(key=_sort_key, reverse=True)
    for item in result:
        item.pop("_sort_key", None)

    return result


@router.post("", response_model=schemas.InvoiceOut)
def create_invoice(
    factura: schemas.InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = get_tenant_uuid(request)
    created = factura_crud.create_with_line_items(db, tenant_id, factura)
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="create",
            entity_type="invoice",
            entity_id=str(getattr(created, "id", None)),
            actor_type="user" if user_id else "system",
            source="api",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"status": getattr(created, "status", None)},
            req=request,
        )
    except Exception:
        pass
    return created


@router.put("/{factura_id}", response_model=schemas.InvoiceOut)
def update_invoice(
    factura_id: UUID,
    factura: schemas.InvoiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a draft invoice."""
    from sqlalchemy.orm import joinedload

    tenant_id = get_tenant_uuid(request)

    factura_uuid = factura_id
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.lines),
            joinedload(Invoice.customer),
        )
        .filter(Invoice.id == factura_uuid, Invoice.tenant_id == tenant_id)
        .first()
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be edited")

    # Update allowed fields.
    update_data = factura.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        if hasattr(invoice, field):
            setattr(invoice, field, value)

    db.commit()
    db.refresh(invoice, ["lines", "customer"])
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="update",
            entity_type="invoice",
            entity_id=str(invoice.id),
            actor_type="user" if user_id else "system",
            source="api",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"fields": sorted(update_data.keys())} if update_data else None,
            req=request,
        )
    except Exception:
        pass

    return invoice


@router.delete("/{factura_id}")
def void_invoice(factura_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Void an invoice."""
    tenant_id = get_tenant_uuid(request)

    factura_uuid = factura_id
    invoice = (
        db.query(Invoice).filter(Invoice.id == factura_uuid, Invoice.tenant_id == tenant_id).first()
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Paid invoices cannot be voided.")

    invoice.status = "voided"
    db.commit()
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="void",
            entity_type="invoice",
            entity_id=str(invoice.id),
            actor_type="user" if user_id else "system",
            source="api",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"status": "void", "number": invoice.number},
            req=request,
        )
    except Exception:
        pass

    return {"status": "ok", "message": f"Invoice {invoice.number} voided"}


@router.post("/{factura_id}/issue", response_model=schemas.InvoiceOut)
@router.post("/{factura_id}/emitir", response_model=schemas.InvoiceOut)
def issue_invoice(
    factura_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    tenant_id = get_tenant_uuid(request)
    issued = factura_crud.issue_invoice(db, tenant_id, factura_id)
    # Reload with relations
    issued = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.lines),
            joinedload(Invoice.customer),
        )
        .filter_by(id=issued.id)
        .first()
    )
    try:
        claims = getattr(request.state, "access_claims", None)
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        audit_event(
            db,
            action="issue",
            entity_type="invoice",
            entity_id=str(issued.id),
            actor_type="user" if user_id else "system",
            source="api",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            changes={"status": issued.status, "number": issued.number},
            req=request,
        )
    except Exception:
        pass
    return issued


@router.get("/{factura_id}")
def get_invoice_by_id(
    factura_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    tenant_id = get_tenant_uuid(request)
    factura = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.lines),
            joinedload(Invoice.customer),
        )
        .filter_by(id=factura_id, tenant_id=tenant_id)
        .first()
    )

    # If the record does not exist in Invoice, look it up in Document (POS).
    if not factura:
        doc_row = (
            db.query(Document)
            .filter(Document.id == factura_id, Document.tenant_id == tenant_id)
            .first()
        )
        if doc_row:
            payload = doc_row.payload or {}
            doc_model_data = payload
        else:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Serialize the POS document payload.
        totals = doc_model_data.get("totals") or {}
        buyer = doc_model_data.get("buyer") or {}
        doc_info = doc_model_data.get("document") or {}
        lines_raw = doc_model_data.get("lines") or []
        series = doc_info.get("series") or ""
        sequential = doc_info.get("sequential") or ""
        numero = (
            f"{series}-{sequential}"
            if series and sequential
            else (series or sequential or str(factura_id)[:8])
        )
        lines = [
            {
                "sector": "pos",
                "description": ln.get("name", ""),
                "quantity": float(ln.get("qty", 0) or 0),
                "unit_price": float(ln.get("unitPrice", 0) or 0),
                "tax_rate": sum(float(t.get("amount", 0) or 0) for t in (ln.get("taxLines") or [])),
            }
            for ln in lines_raw
        ]
        return {
            "id": str(factura_id),
            "number": numero,
            "issue_date": doc_info.get("issuedAt"),
            "status": (doc_info.get("status") or "").lower(),
            "subtotal": float(totals.get("subtotal") or 0),
            "tax": float(totals.get("taxTotal") or 0),
            "total": float(totals.get("grandTotal") or 0),
            "customer": {
                "name": buyer.get("name") or buyer.get("businessName") or "",
                "tax_id": buyer.get("idNumber") or "",
                "email": "",
            },
            "lines": lines,
            "source": "document",
        }

    if not factura:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Ensure explicit line serialization to avoid polymorphism issues.
    line_items = [
        {
            "sector": getattr(line_item, "sector", None),
            "description": getattr(line_item, "description", ""),
            "quantity": float(getattr(line_item, "quantity", 0) or 0),
            "unit_price": float(getattr(line_item, "unit_price", 0) or 0),
            "tax_rate": float(getattr(line_item, "vat", 0) or 0),
            "pos_receipt_line_id": getattr(line_item, "pos_receipt_line_id", None),
        }
        for line_item in getattr(factura, "lines", []) or []
    ]

    cliente_obj = factura.customer
    cliente = None
    if cliente_obj:
        cliente = {
            "id": getattr(cliente_obj, "id", None),
            "name": getattr(cliente_obj, "name", "") or "",
            "email": getattr(cliente_obj, "email", "") or "",
            "tax_id": getattr(cliente_obj, "tax_id", "")
            or "",
        }

    return {
        "id": factura.id,
        "number": factura.number,
        "issue_date": factura.issue_date,
        "status": factura.status,
        "subtotal": getattr(factura, "subtotal", None),
        "tax": getattr(factura, "vat", None),
        "total": getattr(factura, "total", getattr(factura, "amount", None)),
        "customer": cliente,
        "lines": line_items,
    }


@router.get("/{factura_id}/pdf", response_class=Response)
def descargar_pdf(
    factura_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = get_tenant_uuid(request)
    factura = db.query(Invoice).filter_by(id=factura_id, tenant_id=tenant_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # Render with Jinja2 (vertical-specific template if present).
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from weasyprint import HTML

        # Load PDF templates.
        base_dir = Path(__file__).resolve().parents[5]  # apps/backend
        tmpl_dir = base_dir / "app" / "templates" / "pdf"
        env = Environment(
            loader=FileSystemLoader(str(tmpl_dir)),
            autoescape=select_autoescape(["html"]),
        )

        # Simple template selection (future: tenant/vertical-aware).
        tmpl_name = os.getenv("INVOICE_PDF_TEMPLATE", "invoice_base.html")
        template = env.get_template(tmpl_name)

        # Render lines if the ORM relation is loaded.
        lines = getattr(factura, "lines", [])
        html = template.render(factura=factura, lines=lines)
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{factura.id}.pdf"},
        )
    except Exception:
        raise HTTPException(
            status_code=501,
            detail="PDF renderer/template not available (install WeasyPrint/Jinja2)",
        )


@router.patch("/{factura_id}/mark-paid")
@router.patch("/{factura_id}/marcar-cobrada")
def marcar_cobrada(factura_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Mark a credit sale (PENDING_PAYMENT) as paid (ISSUED)."""
    tenant_id = get_tenant_uuid(request)
    doc = (
        db.query(Document)
        .filter(Document.id == factura_id, Document.tenant_id == tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "PENDING_PAYMENT":
        raise HTTPException(status_code=400, detail="The document is not pending payment")
    doc.status = "ISSUED"
    db.commit()
    return {"ok": True, "id": str(factura_id), "status": "ISSUED"}
