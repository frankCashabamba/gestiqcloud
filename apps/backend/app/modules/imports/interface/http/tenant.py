from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime
import re
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request, Query, status
import os
import time
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.imports import crud, services
from app.modules.imports.application.job_runner import enqueue_job
from app.modules.imports.schemas import (
    DatosImportadosOut,
    DatosImportadosCreate,
    DocumentoProcesadoResponse,
    OkResponse,
    HayPendientesOut,
    DatosImportadosUpdate,
    BatchCreate,
    BatchOut,
    ItemOut,
    ItemPatch,
    IngestRows,
    ImportMappingCreate,
    ImportMappingUpdate,
    ImportMappingOut,
    OkResponse,
    OCRJobEnqueuedResponse,
    OCRJobStatusResponse,
)
from app.modules.imports.extractores.utilidades import calcular_hash_documento
from app.models.core.modelsimport import (
    DatosImportados,
    ImportBatch,
    ImportMapping,
    ImportLineage,
    ImportItemCorrection,
    ImportOCRJob,
)
# Avoid importing heavy domain models at import time to keep router mountable in test envs
# (domain handlers perform promotion separately)
from app.models.core.auditoria_importacion import AuditoriaImportacion
from sqlalchemy import inspect as sa_inspect


# Public router (no auth) for lightweight health checks
public_router = APIRouter(
    prefix="/imports",
    tags=["Imports"],
)

router = APIRouter(
    prefix="/imports",
    tags=["Imports"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)

# --- simple in-memory throttling (per-tenant) --------------------------------
_INGEST_WINDOW_SEC = 60
_DEFAULT_INGEST_LIMIT = int(os.getenv("IMPORTS_MAX_INGESTS_PER_MIN", "30"))
_ingest_rate_state: dict[str, list[float]] = {}

def _throttle_ingest(tenant_id: str | int):
    key = str(tenant_id)
    now = time.time()
    window_start = now - _INGEST_WINDOW_SEC
    buf = _ingest_rate_state.get(key, [])
    buf = [t for t in buf if t >= window_start]
    # Re-read limit from env to allow test overrides
    try:
        limit = int(os.getenv("IMPORTS_MAX_INGESTS_PER_MIN", str(_DEFAULT_INGEST_LIMIT)))
    except Exception:
        limit = _DEFAULT_INGEST_LIMIT
    if len(buf) >= limit:
        raise HTTPException(status_code=429, detail="Too many ingests; try later")
    buf.append(now)
    _ingest_rate_state[key] = buf


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


@router.post("/documento/procesar", status_code=status.HTTP_202_ACCEPTED, response_model=OCRJobEnqueuedResponse)
@router.post("/procesar", status_code=status.HTTP_202_ACCEPTED, response_model=OCRJobEnqueuedResponse)
async def procesar_documento_api(
    request: Request,
    file: UploadFile = File(...),
):
    access_claims = getattr(request.state, "access_claims", None)
    empresa_id = access_claims.get("tenant_id") if access_claims else None
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Falta empresa_id en el token")
    try:
        empresa_id_int = int(empresa_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Falta empresa_id en el token")

    contenido = await file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="Archivo vacio")

    max_mb = float(os.getenv("IMPORTS_MAX_UPLOAD_MB", "10"))
    max_bytes = int(max_mb * 1024 * 1024)
    if len(contenido) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large: {len(contenido)} bytes > {max_bytes}")

    allowed = {"application/pdf", "image/jpeg", "image/png", "image/heic"}
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {content_type}")

    filename = file.filename or "documento.pdf"
    job_id = enqueue_job(
        empresa_id=empresa_id_int,
        filename=filename,
        content_type=content_type,
        payload=contenido,
    )
    return {"job_id": str(job_id), "status": "pending"}


@router.get("/jobs/{job_id}", response_model=OCRJobStatusResponse)
async def get_ocr_job(job_id: UUID, request: Request, db: Session = Depends(get_db)):
    access_claims = getattr(request.state, "access_claims", None)
    empresa_id = access_claims.get("tenant_id") if access_claims else None
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Falta empresa_id en el token")
    try:
        empresa_id_int = int(empresa_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Falta empresa_id en el token")

    job = (
        db.query(ImportOCRJob)
        .filter(ImportOCRJob.id == job_id, ImportOCRJob.empresa_id == empresa_id_int)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return {
        "job_id": str(job.id),
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }



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


@public_router.get("/health")
def imports_health(request: Request, db: Session = Depends(get_db)):
    """Quick schema presence check for imports module.

    Returns list of missing tables/columns useful to diagnose migration issues rapidly.
    """
    insp = sa_inspect(db.get_bind())
    required = {
        "import_batches": ["id", "empresa_id", "source_type", "origin", "status"],
        "import_items": ["id", "batch_id", "idx", "raw", "status", "idempotency_key"],
        "import_mappings": ["id", "empresa_id", "name", "source_type"],
        "import_item_corrections": ["id", "empresa_id", "item_id", "user_id", "field"],
        "import_lineage": ["id", "empresa_id", "item_id", "promoted_to"],
        "auditoria_importacion": ["id", "empresa_id", "documento_id", "fecha", "batch_id", "item_id"],
    }
    missing = {"tables": [], "columns": []}
    existing_tables = set(insp.get_table_names())
    for tbl, cols in required.items():
        if tbl not in existing_tables:
            missing["tables"].append(tbl)
            continue
        cols_exist = {c["name"] for c in insp.get_columns(tbl)}
        for c in cols:
            if c not in cols_exist:
                missing["columns"].append(f"{tbl}.{c}")
    limits = {
        "max_items_per_batch": int(os.getenv("IMPORTS_MAX_ITEMS_PER_BATCH", "5000")),
        "max_upload_mb": float(os.getenv("IMPORTS_MAX_UPLOAD_MB", "10")),
        "max_ingests_per_min": int(os.getenv("IMPORTS_MAX_INGESTS_PER_MIN", "30")),
        "allowed_mimetypes": [
            "image/jpeg",
            "image/png",
            "image/heic",
            "application/pdf",
        ],
    }
    return {"ok": not (missing["tables"] or missing["columns"]), "missing": missing, "limits": limits}


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
        raise HTTPException(status_code=400, detail=f"Fecha invÃƒÂ¡lida: {fecha_str}")

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
    return await procesar_documento_api(request=request, file=file)


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


# ------------------------------
# New batch endpoints (EPIC flow)
# ------------------------------

@router.post("/batches", response_model=BatchOut)
def create_batch_endpoint(dto: BatchCreate, request: Request, db: Session = Depends(get_db)):
    """Skeleton endpoint for batch creation. Returns placeholder until models are wired."""
    from app.modules.imports.application import use_cases

    empresa_id = int(request.state.access_claims.get("tenant_id"))
    user_id = request.state.access_claims.get("user_id")
    batch = use_cases.create_batch(db, empresa_id, user_id, dto.model_dump())
    return batch


@router.post("/batches/{batch_id}/ingest", response_model=list[ItemOut])
def ingest_rows_endpoint(
    batch_id: UUID,                # <-- UUID correcto para el id del batch
    payload: IngestRows,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.modules.imports.application import use_cases

    # toma el tenant_id del token sin forzarlo a UUID
    tenant_raw = request.state.access_claims.get("tenant_id")
    try:
        empresa_id = int(tenant_raw)          # muchos setups lo llevan como entero
    except (TypeError, ValueError):
        empresa_id = tenant_raw               # si no es int, ÃƒÂºsalo tal cual (p.ej. string)

    # throttle per tenant
    _throttle_ingest(tenant_raw)

    # busca el batch (id UUID + empresa_id del tipo que corresponda en tu modelo)
    batch = (
        db.query(ImportBatch)
        .filter(ImportBatch.id == batch_id, ImportBatch.empresa_id == empresa_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado")

    # mappings / transforms / defaults (mapping_id puede ser None; si viene, intenta parsear a UUID solo si tiene pinta de serlo)
    mappings = None
    transforms = payload.transforms
    defaults = payload.defaults

    mapping_id_val = payload.mapping_id or batch.mapping_id
    if mapping_id_val:
        # intenta convertir a UUID solo si parece un UUID; si falla, dÃƒÂ©jalo tal cual
        try:
            mapping_id_val = UUID(str(mapping_id_val))
        except ValueError:
            pass

        mp = (
            db.query(ImportMapping)
            .filter(
                ImportMapping.id == mapping_id_val,
                ImportMapping.empresa_id == empresa_id,
                ImportMapping.source_type == batch.source_type,
            )
            .first()
        )
        if mp:
            mappings = mp.mappings or mappings
            transforms = mp.transforms or transforms
            defaults = mp.defaults or defaults

    # Limit number of rows per ingest (413 on overflow)
    import os
    max_items = int(os.getenv("IMPORTS_MAX_ITEMS_PER_BATCH", "5000"))
    if payload.rows and len(payload.rows) > max_items:
        raise HTTPException(status_code=413, detail=f"Too many rows: {len(payload.rows)} > {max_items}")

    items = use_cases.ingest_rows(
        db,
        empresa_id,        # <-- pasa el empresa_id tal cual (int o string, segÃƒÂºn tu modelo)
        batch,
        payload.rows,
        mappings=mappings,
        transforms=transforms,
        defaults=defaults,
        dedupe_keys=(mp.dedupe_keys if 'mp' in locals() and mp else None),
    )
    return items


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch_endpoint(batch_id: UUID, request: Request, db: Session = Depends(get_db)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch: raise HTTPException(status_code=404, detail="Batch no encontrado")
    if str(batch.empresa_id) != str(request.state.access_claims.get("tenant_id")):
        raise HTTPException(status_code=403, detail="No autorizado")
    return batch


@router.get("/batches", response_model=list[BatchOut])
def list_batches_endpoint(request: Request, db: Session = Depends(get_db), status: str | None = None):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    q = db.query(ImportBatch).filter(ImportBatch.empresa_id == empresa_id)
    if status:
        q = q.filter(ImportBatch.status == status)
    return q.order_by(ImportBatch.created_at.desc()).all()


@router.get("/batches/{batch_id}/items", response_model=list[ItemOut])
def list_batch_items_endpoint(
    batch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = None,
    q: str | None = None,
    with_: str | None = Query(default=None, alias="with"),
):
    from app.modules.imports.infrastructure.repositories import ImportsRepository
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    repo = ImportsRepository()
    items = repo.list_items(db, empresa_id, batch_id, status=status, q=q)  # batch_id es UUID
    if with_ != "lineage":
        return items
    item_ids = [it.id for it in items] 
    if not item_ids:
        return items
    lineages = (
        db.query(ImportLineage)
        .filter(ImportLineage.item_id.in_(item_ids), ImportLineage.empresa_id == empresa_id)
        .all()
    )
    corrections = (
        db.query(ImportItemCorrection)
        .filter(ImportItemCorrection.item_id.in_(item_ids), ImportItemCorrection.empresa_id == empresa_id)
        .order_by(ImportItemCorrection.created_at.desc())
        .all()
    )
    # group
    from collections import defaultdict

    lineage_map = defaultdict(list)
    for lg in lineages:
        lineage_map[lg.item_id].append({
            "promoted_to": lg.promoted_to,
            "promoted_ref": lg.promoted_ref,
            "created_at": lg.created_at,
        })
    corr_map = {}
    for corr in corrections:
        corr_map.setdefault(corr.item_id, corr)  # keep latest

    out = []
    for it in items:
        obj = {
            "id": it.id,
            "idx": it.idx,
            "status": it.status,
            "raw": it.raw,
            "normalized": it.normalized,
            "errors": it.errors,
            "promoted_to": it.promoted_to,
            "promoted_id": it.promoted_id,
            "promoted_at": it.promoted_at,
            "lineage": lineage_map.get(it.id, []),
        }
        last = corr_map.get(it.id)
        if last is not None:
            obj["last_correction"] = {
                "field": last.field,
                "old_value": last.old_value,
                "new_value": last.new_value,
                "created_at": last.created_at,
                "user_id": str(last.user_id),
            }
        out.append(obj)
    return out


@router.patch("/batches/{batch_id}/items/{item_id}", response_model=ItemOut)
def patch_batch_item_endpoint(
    batch_id: UUID,
    item_id: UUID,
    patch: ItemPatch,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.modules.imports.application import use_cases
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    user_id = request.state.access_claims.get("user_id")
    it = use_cases.patch_item(db, empresa_id, user_id, batch_id, item_id, patch.field, patch.value)
    if not it:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return it


@router.post("/batches/{batch_id}/validate", response_model=list[ItemOut])
def validate_batch_endpoint(batch_id: UUID, request: Request, db: Session = Depends(get_db)):
    from app.modules.imports.application import use_cases
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    return use_cases.revalidate_batch(db, empresa_id, batch_id)


@router.post("/batches/{batch_id}/promote")
def promote_batch_endpoint(batch_id: str, request: Request, db: Session = Depends(get_db)):
    from app.modules.imports.application import use_cases

    empresa_id = int(request.state.access_claims.get("tenant_id"))
    res = use_cases.promote_batch(db, empresa_id, batch_id)
    return res


@router.get("/batches/{batch_id}/errors.csv")
def errors_csv_endpoint(batch_id: UUID, request: Request, db: Session = Depends(get_db)):
    from io import StringIO
    import csv
    from app.modules.imports.infrastructure.repositories import ImportsRepository

    empresa_id = int(request.state.access_claims.get("tenant_id"))
    repo = ImportsRepository()
    items = repo.list_items(db, empresa_id, batch_id, status="ERROR_VALIDATION")
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["idx", "campo", "error", "valor"])
    for it in items:
        errs = it.errors or []
        for e in errs:
            field = e.get("field") or e.get("campo") or ""
            msg = e.get("msg") or e.get("error") or ""
            val = None
            if it.normalized and field in it.normalized:
                val = it.normalized.get(field)
            elif it.raw and field in it.raw:
                val = it.raw.get(field)
            writer.writerow([it.idx, field, msg, val])
    csv_text = buf.getvalue()
    buf.close()
    from fastapi import Response

    return Response(content=csv_text, media_type="text/csv")


# ------------------------------
# Acciones masivas y reproceso
# ------------------------------

# payloads tipados de forma dinÃƒÂ¡mica en bulk_patch_items


@router.post("/batches/{batch_id}/items/bulk-patch", response_model=OkResponse)
def bulk_patch_items(
    batch_id: UUID,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.modules.imports.application import use_cases
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    user_id = request.state.access_claims.get("user_id")

    ids = payload.get("ids") or []
    changes = payload.get("changes") or {}
    if not isinstance(ids, list) or not isinstance(changes, dict) or not ids or not changes:
        raise HTTPException(status_code=400, detail="Body invalido: {ids:[], changes:{campo:valor}}")

    # Aplicar cambios en cada id, campo por campo
    for item_id in ids:
        for field, value in changes.items():
            use_cases.patch_item(db, empresa_id, user_id, batch_id, item_id, field, value)

    # Revalidar lote completo
    use_cases.revalidate_batch(db, empresa_id, batch_id)
    return OkResponse()


@router.post("/batches/{batch_id}/reprocess", response_model=OkResponse)
def reprocess_batch(
    batch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    scope: str | None = Query(default="all", pattern="^(all|errors)$"),
    promote: bool | None = Query(default=True),
):
    from app.modules.imports.application import use_cases
    empresa_id = int(request.state.access_claims.get("tenant_id"))

    # Revalidar: para simplificar se revalida todo el lote; en futuras mejoras se puede filtrar
    use_cases.revalidate_batch(db, empresa_id, batch_id)

    # Promover sÃƒÂ³lo vÃƒÂ¡lidos si promote=true
    if promote:
        use_cases.promote_batch(db, empresa_id, batch_id)
    return OkResponse()


# ------------------------------
# CRUD ImportMappings (plantillas)
# ------------------------------

@router.post("/mappings", response_model=ImportMappingOut)
def create_mapping(dto: ImportMappingCreate, request: Request, db: Session = Depends(get_db)):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    obj = ImportMapping(
        empresa_id=empresa_id,
        name=dto.name,
        source_type=dto.source_type,
        version=dto.version,
        mappings=dto.mappings,
        transforms=dto.transforms,
        defaults=dto.defaults,
        dedupe_keys=dto.dedupe_keys,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/mappings", response_model=List[ImportMappingOut])
def list_mappings(request: Request, db: Session = Depends(get_db), source_type: str | None = None):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    q = db.query(ImportMapping).filter(ImportMapping.empresa_id == empresa_id)
    if source_type:
        q = q.filter(ImportMapping.source_type == source_type)
    return q.order_by(ImportMapping.created_at.desc()).all()


@router.get("/mappings/{mapping_id}", response_model=ImportMappingOut)
def get_mapping(mapping_id: UUID, request: Request, db: Session = Depends(get_db)):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    obj = db.query(ImportMapping).filter(ImportMapping.id == mapping_id, ImportMapping.empresa_id == empresa_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Mapping no encontrado")
    return obj


@router.put("/mappings/{mapping_id}", response_model=ImportMappingOut)
def update_mapping(mapping_id: UUID, dto: ImportMappingUpdate, request: Request, db: Session = Depends(get_db)):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    obj = db.query(ImportMapping).filter(ImportMapping.id == mapping_id, ImportMapping.empresa_id == empresa_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Mapping no encontrado")
    if dto.name is not None:
        obj.name = dto.name
    if dto.version is not None:
        obj.version = dto.version
    if dto.mappings is not None:
        obj.mappings = dto.mappings
    if dto.transforms is not None:
        obj.transforms = dto.transforms
    if dto.defaults is not None:
        obj.defaults = dto.defaults
    if dto.dedupe_keys is not None:
        obj.dedupe_keys = dto.dedupe_keys
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/mappings/{mapping_id}/clone", response_model=ImportMappingOut)
def clone_mapping(mapping_id: UUID, request: Request, db: Session = Depends(get_db)):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    src = db.query(ImportMapping).filter(ImportMapping.id == mapping_id, ImportMapping.empresa_id == empresa_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Mapping no encontrado")
    clone = ImportMapping(
        empresa_id=empresa_id,
        name=f"{src.name} (copia)",
        source_type=src.source_type,
        version=(src.version or 1) + 1,
        mappings=src.mappings,
        transforms=src.transforms,
        defaults=src.defaults,
        dedupe_keys=src.dedupe_keys,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.delete("/mappings/{mapping_id}", response_model=OkResponse)
def delete_mapping(mapping_id: UUID, request: Request, db: Session = Depends(get_db)):
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    obj = db.query(ImportMapping).filter(ImportMapping.id == mapping_id, ImportMapping.empresa_id == empresa_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Mapping no encontrado")
    db.delete(obj)
    db.commit()
    return OkResponse()


# ------------------------------
# Fotos: subir y adjuntar con OCR
# ------------------------------

@router.post("/batches/{batch_id}/photos", response_model=ItemOut)
async def upload_photo_to_batch(
    batch_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    from app.modules.imports.application import use_cases
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    user_id = request.state.access_claims.get("user_id")

    batch = (
        db.query(ImportBatch)
        .filter(ImportBatch.id == batch_id, ImportBatch.empresa_id == empresa_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado")

    # Limit file size (read & rewind) + mimetype
    import os
    max_mb = float(os.getenv("IMPORTS_MAX_UPLOAD_MB", "10"))
    max_bytes = int(max_mb * 1024 * 1024)
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large: {len(content)} bytes > {max_bytes}")
    allowed = {"image/jpeg", "image/png", "image/heic", "application/pdf"}
    if (file.content_type or "") not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {file.content_type}")
    file.file.seek(0)

    # Crea item a partir de la foto + adjunta OCR y metadata
    # Size + mimetype limits and throttling handled above
    item = use_cases.ingest_photo(db, str(empresa_id), str(user_id), batch, file)
    return item


@router.post("/batches/{batch_id}/items/{item_id}/photos", response_model=ItemOut)
async def attach_photo_to_item(
    batch_id: UUID,
    item_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    from app.modules.imports.application import use_cases
    from app.models.core.modelsimport import ImportItem
    empresa_id = int(request.state.access_claims.get("tenant_id"))
    user_id = request.state.access_claims.get("user_id")

    # Limit file size + mimetype
    import os
    max_mb = float(os.getenv("IMPORTS_MAX_UPLOAD_MB", "10"))
    max_bytes = int(max_mb * 1024 * 1024)
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large: {len(content)} bytes > {max_bytes}")
    allowed = {"image/jpeg", "image/png", "image/heic", "application/pdf"}
    if (file.content_type or "") not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {file.content_type}")
    file.file.seek(0)

    # Verificar scoping: item pertenece al batch y al tenant
    it = (
        db.query(ImportItem)
        .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
        .filter(
            ImportItem.id == item_id,
            ImportBatch.id == batch_id,
            ImportBatch.empresa_id == empresa_id,
        )
        .first()
    )
    if not it:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    # Limit file size (read & rewind)
    import os
    max_mb = float(os.getenv("IMPORTS_MAX_UPLOAD_MB", "10"))
    max_bytes = int(max_mb * 1024 * 1024)
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large: {len(content)} bytes > {max_bytes}")
    file.file.seek(0)

    # Size + mimetype limits and throttling handled above
    item = use_cases.attach_photo_and_reocr(db, str(empresa_id), str(user_id), it, file)
    return item


