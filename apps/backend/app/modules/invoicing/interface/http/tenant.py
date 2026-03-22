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
    tags=["Facturacion"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("")
def listar_facturas_principales(
    request: Request,
    db: Session = Depends(get_db),
    estado: str | None = Query(None),
    q: str | None = Query(None),
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
):
    from datetime import datetime

    tenant_id = get_tenant_uuid(request)

    # ── 1. Facturas del módulo clásico (Invoice) ──────────────────────────────
    old_invoices = factura_crud.obtener_facturas_principales(
        db=db, tenant_id=tenant_id, estado=estado, q=q, desde=desde, hasta=hasta
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
                "numero": inv.number,
                "fecha_emision": _iso(inv.issue_date),
                "estado": inv.status,
                "subtotal": float(inv.subtotal) if inv.subtotal is not None else None,
                "iva": float(inv.vat) if inv.vat is not None else None,
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

    if estado:
        doc_q = doc_q.filter(Document.status == estado.upper())
    if desde:
        try:
            doc_q = doc_q.filter(
                Document.issued_at >= datetime.strptime(desde, "%Y-%m-%d").replace(tzinfo=UTC)
            )
        except ValueError:
            pass
    if hasta:
        try:
            doc_q = doc_q.filter(
                Document.issued_at <= datetime.strptime(hasta, "%Y-%m-%d").replace(tzinfo=UTC)
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
                "numero": numero,
                "fecha_emision": _iso(doc.issued_at),
                "date": _iso(doc.issued_at),
                "estado": doc.status.lower(),
                "subtotal": (
                    float(totals["subtotal"]) if totals.get("subtotal") is not None else None
                ),
                "iva": float(totals["taxTotal"]) if totals.get("taxTotal") is not None else None,
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


@router.post("", response_model=schemas.InvoiceCreate)
def crear_factura(
    factura: schemas.InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = get_tenant_uuid(request)
    created = factura_crud.create_with_lineas(db, tenant_id, factura)
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
def actualizar_factura(
    factura_id: UUID,
    factura: schemas.InvoiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Actualizar factura en borrador"""
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
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if invoice.status not in ["draft", "borrador"]:
        raise HTTPException(status_code=400, detail="Solo se pueden editar facturas en borrador")

    # Actualizar campos permitidos
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
def anular_factura(factura_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Anular factura (soft delete)"""
    tenant_id = get_tenant_uuid(request)

    factura_uuid = factura_id
    invoice = (
        db.query(Invoice).filter(Invoice.id == factura_uuid, Invoice.tenant_id == tenant_id).first()
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if invoice.status == "paid":
        raise HTTPException(
            status_code=400,
            detail="No se puede anular una factura pagada. Use abonos/créditos.",
        )

    invoice.status = "void"
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

    return {"status": "ok", "message": f"Factura {invoice.number} anulada"}


@router.post("/{factura_id}/emitir", response_model=schemas.InvoiceOut)
def emitir_factura(
    factura_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    tenant_id = get_tenant_uuid(request)
    issued = factura_crud.emitir_factura(db, tenant_id, factura_id)
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
def obtener_factura_por_id(
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

    # Si no está en Invoice, buscar en Document (POS)
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
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        # Serializar desde payload del documento POS
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
        lineas = [
            {
                "description": ln.get("name", ""),
                "cantidad": float(ln.get("qty", 0) or 0),
                "precio_unitario": float(ln.get("unitPrice", 0) or 0),
                "iva": sum(float(t.get("amount", 0) or 0) for t in (ln.get("taxLines") or [])),
            }
            for ln in lines_raw
        ]
        return {
            "id": str(factura_id),
            "numero": numero,
            "fecha_emision": doc_info.get("issuedAt"),
            "estado": (doc_info.get("status") or "").lower(),
            "subtotal": float(totals.get("subtotal") or 0),
            "iva": float(totals.get("taxTotal") or 0),
            "total": float(totals.get("grandTotal") or 0),
            "cliente": {
                "name": buyer.get("name") or buyer.get("businessName") or "",
                "identificacion": buyer.get("idNumber") or "",
                "email": "",
            },
            "lineas": lineas,
            "lines": lineas,
            "source": "document",
        }

    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Asegurar serialización explícita de líneas (evita problemas de polimorfismo)
    lineas = [
        {
            "sector": getattr(line_item, "sector", None),
            "description": getattr(line_item, "description", ""),
            "cantidad": float(getattr(line_item, "quantity", 0) or 0),
            "precio_unitario": float(getattr(line_item, "unit_price", 0) or 0),
            "iva": float(getattr(line_item, "vat", 0) or 0),
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
            "identificacion": getattr(cliente_obj, "identificacion", "") or "",
        }

    return {
        "id": factura.id,
        "numero": factura.number,
        "fecha_emision": factura.issue_date,
        "estado": factura.status,
        "subtotal": getattr(factura, "subtotal", None),
        "iva": getattr(factura, "vat", None),
        "total": getattr(factura, "total", getattr(factura, "amount", None)),
        "cliente": cliente,
        "lineas": lineas,
        "lines": lineas,
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
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    # Render con Jinja2 (template por vertical si existe)
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from weasyprint import HTML

        # Cargar templates PDF
        base_dir = Path(__file__).resolve().parents[5]  # apps/backend
        tmpl_dir = base_dir / "app" / "templates" / "pdf"
        env = Environment(
            loader=FileSystemLoader(str(tmpl_dir)),
            autoescape=select_autoescape(["html"]),
        )

        # Selección simple de template (futuro: según tenant/vertical)
        tmpl_name = os.getenv("INVOICE_PDF_TEMPLATE", "invoice_base.html")
        template = env.get_template(tmpl_name)

        # Relación de líneas si está mapeada en ORM
        lineas = getattr(factura, "lines", [])
        html = template.render(factura=factura, lineas=lineas)
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{factura.id}.pdf"},
        )
    except Exception:
        raise HTTPException(
            status_code=501,
            detail="Renderizador PDF/plantilla no disponible (instala WeasyPrint/Jinja2)",
        )


@router.patch("/{factura_id}/marcar-cobrada")
def marcar_cobrada(factura_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Marca una venta a crédito (PENDING_PAYMENT) como cobrada (ISSUED)."""
    tenant_id = get_tenant_uuid(request)
    doc = (
        db.query(Document)
        .filter(Document.id == factura_id, Document.tenant_id == tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.status != "PENDING_PAYMENT":
        raise HTTPException(status_code=400, detail="El documento no está pendiente de cobro")
    doc.status = "ISSUED"
    db.commit()
    return {"ok": True, "id": str(factura_id), "status": "ISSUED"}
