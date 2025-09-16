from __future__ import annotations

from typing import List
from datetime import datetime
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.imports import crud, services
from app.modules.imports.schemas import (
    DatosImportadosOut,
    DatosImportadosCreate,
    DocumentoProcesadoResponse,
    OkResponse,
    HayPendientesOut,
    DatosImportadosUpdate,
)
from app.modules.imports.extractores.utilidades import calcular_hash_documento
from app.models.core.modelsimport import DatosImportados
from app.models.core.facturacion import Invoice, BankTransaction, BankAccount, MovimientoTipo
from app.models.core.clients import Cliente
from app.models.core.auditoria_importacion import AuditoriaImportacion


router = APIRouter(
    prefix="/imports",
    tags=["Imports"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.post("/guardar", response_model=DatosImportadosOut)
@router.post("/importar/guardar", response_model=DatosImportadosOut)
def crear_dato_importado(
    data: DatosImportadosCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Falta empresa_id en el token")

    hash_doc = calcular_hash_documento(empresa_id, data.datos)
    duplicado = db.query(DatosImportados).filter_by(hash=hash_doc).first()
    if duplicado:
        raise HTTPException(status_code=400, detail="Documento duplicado")

    data.hash = hash_doc
    return crud.datos_importados_crud.create_with_empresa(db, empresa_id, data)


@router.post("/documento/procesar", response_model=DocumentoProcesadoResponse)
@router.post("/procesar", response_model=DocumentoProcesadoResponse)
async def procesar_documento_api(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    contenido = await file.read()
    filename = file.filename or "documento.pdf"

    documentos = services.procesar_documento(contenido, filename)
    if not documentos:
        raise HTTPException(status_code=422, detail="No se pudieron extraer datos del documento.")

    return {"archivo": filename, "documentos": documentos}


@router.post("/guardar-batch", response_model=List[DatosImportadosOut])
def guardar_batch(
    payload: List[DatosImportadosCreate],
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    out: list[DatosImportados] = []
    for item in payload or []:
        try:
            h = calcular_hash_documento(empresa_id, item.datos)
            dup = db.query(DatosImportados).filter(DatosImportados.hash == h).first()
            if dup:
                continue
            item.hash = h  # type: ignore[attr-defined]
            saved = crud.datos_importados_crud.create_with_empresa(db, empresa_id, item)
            out.append(saved)
        except Exception:
            db.rollback()
            continue
    return out


@router.get("/importar/listar", response_model=List[DatosImportadosOut])
@router.get("/listar", response_model=List[DatosImportadosOut])
def listar_pendientes(
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return db.query(DatosImportados).filter_by(
        empresa_id=empresa_id,
        estado="pendiente",
    ).all()


@router.get("/importar/hay-pendientes", response_model=HayPendientesOut)
@router.get("/hay-pendientes", response_model=HayPendientesOut)
def hay_pendientes(
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    existe = db.query(DatosImportados).filter_by(
        empresa_id=empresa_id,
        estado="pendiente",
    ).first()
    return HayPendientesOut(hayPendientes=bool(existe))


@router.delete("/importar/eliminar/{id}", response_model=OkResponse)
@router.delete("/eliminar/{id}", response_model=OkResponse)
def eliminar_importacion(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    item = db.query(DatosImportados).filter_by(id=id, empresa_id=empresa_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return OkResponse()


@router.put("/actualizar/{id}", response_model=DatosImportadosOut)
def actualizar_importacion(
    id: int,
    data: DatosImportadosUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Permite editar los campos de un registro importado (datos, tipo, estado, hash, origen)."""
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    item = db.query(DatosImportados).filter_by(id=id, empresa_id=empresa_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    # Actualiza solo los campos provistos
    if data.tipo is not None:
        item.tipo = data.tipo
    if data.origen is not None:
        item.origen = data.origen
    if isinstance(data.datos, dict):
        item.datos = data.datos
    if data.estado is not None:
        item.estado = data.estado
    if data.hash is not None:
        item.hash = data.hash

    db.commit()
    db.refresh(item)
    return item


@router.post("/importar/enviar/{id}")
@router.post("/enviar/{id}")
def enviar_documento_final(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    doc_tmp = db.query(DatosImportados).filter_by(id=id, empresa_id=empresa_id).first()
    if not doc_tmp:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    datos = doc_tmp.datos
    fecha_str = datos.get("fecha")
    # Normalizador de fecha: ISO, dd/mm/yyyy, dd-mm-yyyy, yyyy/mm/dd
    def _parse_fecha(s):
        if not isinstance(s, str) or not s.strip():
            return None
        s = s.strip()
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            pass
        m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", s)
        if m:
            d, mth, y = m.groups()
            try:
                return datetime(int(y), int(mth), int(d)).date()
            except Exception:
                pass
        m = re.match(r"^(\d{4})[/-](\d{2})[/-](\d{2})$", s)
        if m:
            y, mth, d = m.groups()
            try:
                return datetime(int(y), int(mth), int(d)).date()
            except Exception:
                pass
        return None
    fecha = _parse_fecha(fecha_str)
    if fecha is None:
        raise HTTPException(status_code=400, detail=f"Fecha inválida: {fecha_str}")

    tipo_str = (datos.get("documentoTipo") or "desconocido").lower()
    try:
        tipo_enum = MovimientoTipo(tipo_str)
    except ValueError:
        tipo_enum = MovimientoTipo.OTRO

    cuenta_ref = datos.get("cuenta")
    cuenta = db.query(BankAccount).filter(
        BankAccount.empresa_id == empresa_id,
        (BankAccount.iban == cuenta_ref) | (BankAccount.nombre == cuenta_ref),
    ).first()
    if not cuenta:
        raise HTTPException(status_code=400, detail=f"Cuenta no encontrada: {cuenta_ref}")
    cuenta_id = cuenta.id

    cliente_nombre = (datos.get("cliente") or "").strip()
    cliente_id = None
    if cliente_nombre:
        cliente_obj = db.query(Cliente).filter(Cliente.nombre == cliente_nombre).first()
        cliente_id = cliente_obj.id if cliente_obj else None

    # Normalizar importe
    try:
        importe_val = float(datos.get("importe") or 0)
    except Exception:
        importe_val = 0.0

    if tipo_str == "factura":
        factura = Invoice(
            numero=datos.get("invoice") or "",
            proveedor=cliente_nombre or "",
            fecha_emision=str(fecha),
            monto=importe_val,
            estado="pendiente",
            empresa_id=empresa_id,
            subtotal=importe_val,
            iva=0,
            total=importe_val,
            cliente_id=cliente_id or 1,
        )
        db.add(factura)
    else:
        movimiento = BankTransaction(
            empresa_id=empresa_id,
            cuenta_id=cuenta_id,
            fecha=fecha,
            importe=importe_val,
            moneda="EUR",
            tipo=tipo_enum,
            concepto=datos.get("concepto") or "",
            categoria=datos.get("categoria"),
            origen=datos.get("origen"),
            cliente_id=cliente_id,
        )
        db.add(movimiento)

    db.delete(doc_tmp)
    db.commit()
    return {"ok": True}


@router.post("/auditoria/guardar")
def guardar_auditoria(
    documento_id: int,
    cambios: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    usuario_id = int(request.state.access_claims.get("user_id"))
    auditoria = AuditoriaImportacion(
        documento_id=documento_id,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        cambios=cambios,
    )
    db.add(auditoria)
    db.commit()
    db.refresh(auditoria)
    return {"ok": True, "auditoria_id": auditoria.id}


@router.get("/auditoria/listar")
def listar_auditoria(
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return (
        db.query(AuditoriaImportacion)
        .filter_by(empresa_id=empresa_id)
        .order_by(AuditoriaImportacion.fecha.desc())
        .all()
    )

# --- Legacy aliases without prefix to keep old paths ---
legacy_router = APIRouter(
    tags=["Imports"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@legacy_router.post("/importar/guardar", response_model=DatosImportadosOut)
def crear_dato_importado_legacy(
    data: DatosImportadosCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    return crear_dato_importado(data, request, db)


@legacy_router.post("/documento/procesar", response_model=DocumentoProcesadoResponse)
async def procesar_documento_api_legacy(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    return await procesar_documento_api(file, request, db)


@legacy_router.get("/importar/listar", response_model=List[DatosImportadosOut])
def listar_pendientes_legacy(
    request: Request,
    db: Session = Depends(get_db),
):
    return listar_pendientes(request, db)


@legacy_router.get("/importar/hay-pendientes")
def hay_pendientes_legacy(
    request: Request,
    db: Session = Depends(get_db),
):
    return hay_pendientes(request, db)


@legacy_router.delete("/importar/eliminar/{id}")
def eliminar_importacion_legacy(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    return eliminar_importacion(id, request, db)


@legacy_router.post("/importar/enviar/{id}")
def enviar_documento_final_legacy(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    return enviar_documento_final(id, request, db)


@legacy_router.post("/auditoria/guardar")
def guardar_auditoria_legacy(
    documento_id: int,
    cambios: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    return guardar_auditoria(documento_id, cambios, request, db)


@legacy_router.get("/auditoria/listar")
def listar_auditoria_legacy(
    request: Request,
    db: Session = Depends(get_db),
):
    return listar_auditoria(request, db)
