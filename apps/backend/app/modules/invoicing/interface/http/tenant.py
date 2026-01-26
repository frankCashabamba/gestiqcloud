from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.audit_events import audit_event
from app.db.rls import ensure_rls
from app.models.core.facturacion import Invoice
from app.modules.invoicing import schemas
from app.modules.invoicing.crud import factura_crud
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session


def _tenant_uuid(request: Request) -> UUID:
    raw = getattr(request.state, "access_claims", {}).get("tenant_id")
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="tenant_id inválido")


router = APIRouter(
    prefix="/invoicing",
    tags=["Facturacion"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[schemas.InvoiceOut])
def listar_facturas_principales(
    request: Request,
    db: Session = Depends(get_db),
    estado: str | None = Query(None),
    q: str | None = Query(None),
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
):
    tenant_id = _tenant_uuid(request)
    return factura_crud.obtener_facturas_principales(
        db=db,
        tenant_id=tenant_id,
        estado=estado,
        q=q,
        desde=desde,
        hasta=hasta,
    )


@router.post("", response_model=schemas.InvoiceCreate)
def crear_factura(
    factura: schemas.InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_uuid(request)
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
    
    tenant_id = _tenant_uuid(request)

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
    tenant_id = _tenant_uuid(request)

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
    
    tenant_id = _tenant_uuid(request)
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


@router.get("/{factura_id}", response_model=schemas.InvoiceOut)
def obtener_factura_por_id(
    factura_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    from sqlalchemy.orm import joinedload
    
    tenant_id = _tenant_uuid(request)
    factura = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.lines),
            joinedload(Invoice.customer),
        )
        .filter_by(id=factura_id, tenant_id=tenant_id)
        .first()
    )
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Asegurar serialización explícita de líneas (evita problemas de polimorfismo)
    lineas = [
        {
            "sector": getattr(l, "sector", None),
            "description": getattr(l, "description", ""),
            "cantidad": float(getattr(l, "quantity", 0) or 0),
            "precio_unitario": float(getattr(l, "unit_price", 0) or 0),
            "iva": float(getattr(l, "vat", 0) or 0),
            "pos_receipt_line_id": getattr(l, "pos_receipt_line_id", None),
        }
        for l in getattr(factura, "lines", []) or []
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
    tenant_id = _tenant_uuid(request)
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
