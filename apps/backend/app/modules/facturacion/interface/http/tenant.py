from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Request
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.facturacion import schemas, services
from app.modules.facturacion.crud import factura_crud
from app.models.core.facturacion import Invoice
from fastapi.responses import Response
from pathlib import Path
import os


router = APIRouter(
tags=["Facturacion"],
dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.get("/", response_model=list[schemas.InvoiceOut])
def listar_facturas_principales(
    request: Request,
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
):
    claims = request.state.access_claims
    empresa_id = int(claims.get("tenant_id"))
    return factura_crud.obtener_facturas_principales(
        db=db,
        empresa_id=empresa_id,
        estado=estado,
        q=q,
        desde=desde,
        hasta=hasta,
    )


@router.post("/", response_model=schemas.InvoiceCreate)
def crear_factura(
    factura: schemas.InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = request.state.access_claims.get("tenant_id")
    return factura_crud.create_with_lineas(db, tenant_id, factura)


@router.put("/{factura_id}", response_model=schemas.InvoiceOut)
def actualizar_factura(
    factura_id: int,
    factura: schemas.InvoiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Actualizar factura en borrador"""
    tenant_id = request.state.access_claims.get("tenant_id")

    invoice = db.query(Invoice).filter(
    Invoice.id == factura_id,
    Invoice.tenant_id == tenant_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if invoice.estado not in ['draft', 'borrador']:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden editar facturas en borrador"
        )
    
    # Actualizar campos permitidos
    update_data = factura.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        if hasattr(invoice, field):
            setattr(invoice, field, value)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.delete("/{factura_id}")
def anular_factura(factura_id: int, request: Request, db: Session = Depends(get_db)):
    """Anular factura (soft delete)"""
    tenant_id = request.state.access_claims.get("tenant_id")

    invoice = db.query(Invoice).filter(
    Invoice.id == factura_id,
    Invoice.tenant_id == tenant_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if invoice.estado == 'paid':
        raise HTTPException(
            status_code=400,
            detail="No se puede anular una factura pagada. Use abonos/créditos."
        )
    
    invoice.estado = 'void'
    db.commit()
    
    return {"status": "ok", "message": f"Factura {invoice.numero} anulada"}


@router.post("/{factura_id}/emitir", response_model=schemas.InvoiceOut)
def emitir_factura(
    factura_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return factura_crud.emitir_factura(db, empresa_id, factura_id)


@router.get("/{factura_id}", response_model=schemas.InvoiceOut)
def obtener_factura_por_id(
    factura_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    factura = db.query(Invoice).filter_by(id=factura_id).first()
    if not factura or factura.empresa_id != empresa_id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura


@router.get("/{factura_id}/pdf", response_class=Response)
def descargar_pdf(
    factura_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    factura = db.query(Invoice).filter_by(id=factura_id, empresa_id=empresa_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    # Render con Jinja2 (template por vertical si existe)
    try:
        from weasyprint import HTML
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        # Cargar templates PDF
        base_dir = Path(__file__).resolve().parents[5]  # apps/backend
        tmpl_dir = base_dir / "app" / "templates" / "pdf"
        env = Environment(loader=FileSystemLoader(str(tmpl_dir)), autoescape=select_autoescape(['html']))

        # Selección simple de template (futuro: según tenant/vertical)
        tmpl_name = os.getenv("INVOICE_PDF_TEMPLATE", "invoice_base.html")
        template = env.get_template(tmpl_name)

        # Relación de líneas si está mapeada en ORM
        lineas = getattr(factura, 'lineas', [])
        html = template.render(factura=factura, lineas=lineas)
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{factura.id}.pdf"
            },
        )
    except Exception:
        raise HTTPException(status_code=501, detail="Renderizador PDF/plantilla no disponible (instala WeasyPrint/Jinja2)")

@router.post("/archivo/procesar")
async def procesar_archivo_factura(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    usuario_id = int(request.state.access_claims.get("user_id"))
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return await services.procesar_archivo_factura(file, usuario_id, empresa_id, db)
