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


router = APIRouter(
    prefix="/facturacion",
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
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return factura_crud.create_with_lineas(db, empresa_id, factura)


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


@router.post("/archivo/procesar")
async def procesar_archivo_factura(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    usuario_id = int(request.state.access_claims.get("user_id"))
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return await services.procesar_archivo_factura(file, usuario_id, empresa_id, db)

