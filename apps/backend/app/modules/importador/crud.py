"""CRUD for imp_documento and imp_log_cambios."""

from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import and_, case, delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.importador import (
    ImpBatchImport,
    ImpBatchItem,
    ImpDocumento,
    ImpIteration,
    ImpLineErrorLog,
    ImpLogCambios,
    ImpReviewSession,
    ImpStagingLine,
)

_REPROCESS_CLEAN_FIELDS = {
    "texto_ocr": None,
    "tipo_documento_detectado": None,
    "confianza_clasificacion": None,
    "requiere_revision": False,
    "datos_extraidos": None,
    "datos_confirmados": None,
    "error_detalle": None,
    "proveedor_detectado": None,
    "ruc_detectado": None,
    "monto_total": None,
    "moneda": None,
    "fecha_documento": None,
    "synced_recipe_id": None,
    "fingerprint_json": None,
    "sheet_profiles_json": None,
    "llm_model": None,
    "raw_ai_json": None,
}


def _is_document_hash_unique_violation(exc: IntegrityError) -> bool:
    message = str(exc).lower()
    return (
        "uq_imp_documento_tenant_hash" in message
        or "imp_documento.tenant_id, imp_documento.hash_sha256" in message
        or "duplicate key value violates unique constraint" in message
        or "unique constraint failed: imp_documento.tenant_id, imp_documento.hash_sha256" in message
    )


def create_documento(db: Session, data: dict) -> ImpDocumento:
    obj = ImpDocumento(**data)
    tenant_id = data.get("tenant_id")
    nombre_archivo = str(data.get("nombre_archivo") or "")
    tamanio_bytes = int(data.get("tamanio_bytes") or 0)
    hash_sha256 = data.get("hash_sha256")
    try:
        with db.begin_nested():
            db.add(obj)
            db.flush()
        return obj
    except IntegrityError as exc:
        if not hash_sha256 or not tenant_id or not _is_document_hash_unique_violation(exc):
            raise
    existing = find_existing_documento(
        db,
        tenant_id,
        nombre_archivo,
        tamanio_bytes,
        hash_sha256,
    )
    if existing:
        return existing
    raise


def create_batch(db: Session, data: dict) -> ImpBatchImport:
    obj = ImpBatchImport(**data)
    db.add(obj)
    db.flush()
    return obj


def create_batch_item(db: Session, data: dict) -> ImpBatchItem:
    obj = ImpBatchItem(**data)
    db.add(obj)
    db.flush()
    return obj


def get_documento(db: Session, doc_id: UUID) -> ImpDocumento | None:
    return (
        db.scalars(
            select(ImpDocumento)
            .options(joinedload(ImpDocumento.logs))
            .where(ImpDocumento.id == doc_id)
        )
        .unique()
        .first()
    )


def get_batch(db: Session, batch_id: UUID, tenant_id: UUID) -> ImpBatchImport | None:
    return (
        db.scalars(
            select(ImpBatchImport)
            .options(joinedload(ImpBatchImport.items))
            .where(
                and_(
                    ImpBatchImport.id == batch_id,
                    ImpBatchImport.tenant_id == tenant_id,
                )
            )
        )
        .unique()
        .first()
    )


def get_batch_any_tenant(db: Session, batch_id: UUID) -> ImpBatchImport | None:
    return (
        db.scalars(
            select(ImpBatchImport)
            .options(joinedload(ImpBatchImport.items))
            .where(ImpBatchImport.id == batch_id)
        )
        .unique()
        .first()
    )


def list_batches(
    db: Session,
    tenant_id: UUID,
    *,
    active_only: bool = False,
    limit: int = 10,
) -> list[ImpBatchImport]:
    q = select(ImpBatchImport).where(ImpBatchImport.tenant_id == tenant_id)
    if active_only:
        q = q.where(ImpBatchImport.estado.in_(("PENDING", "PROCESSING")))
    q = q.order_by(ImpBatchImport.created_at.desc()).limit(limit)
    return db.scalars(q).all()


def list_documentos(
    db: Session, tenant_id: UUID, *, estado: str | None = None, limit: int = 50, offset: int = 0
):
    q = select(ImpDocumento).where(ImpDocumento.tenant_id == tenant_id)
    if estado:
        q = q.where(ImpDocumento.estado == estado)
    q = q.order_by(ImpDocumento.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(q).all()


def update_documento(db: Session, doc: ImpDocumento, data: dict) -> ImpDocumento:
    for k, v in data.items():
        setattr(doc, k, v)
    db.flush()
    return doc


def clear_document_iteration_state(db: Session, documento_id: UUID) -> None:
    iteration_ids = list(
        db.scalars(select(ImpIteration.id).where(ImpIteration.documento_id == documento_id)).all()
    )
    if iteration_ids:
        db.execute(delete(ImpLineErrorLog).where(ImpLineErrorLog.iteration_id.in_(iteration_ids)))
    db.execute(delete(ImpReviewSession).where(ImpReviewSession.documento_id == documento_id))
    db.execute(delete(ImpIteration).where(ImpIteration.documento_id == documento_id))
    db.execute(delete(ImpStagingLine).where(ImpStagingLine.documento_id == documento_id))
    db.flush()


def reset_documento_for_reprocess(
    db: Session,
    doc: ImpDocumento,
    *,
    estado: str,
    recipe_snapshot_id: UUID | None | object = None,
    clear_recipe_snapshot: bool = False,
) -> ImpDocumento:
    clear_document_iteration_state(db, doc.id)
    payload = dict(_REPROCESS_CLEAN_FIELDS)
    payload["estado"] = estado
    if clear_recipe_snapshot:
        payload["recipe_snapshot_id"] = None
    elif recipe_snapshot_id is not None:
        payload["recipe_snapshot_id"] = recipe_snapshot_id
    return update_documento(db, doc, payload)


def update_batch(db: Session, batch: ImpBatchImport, data: dict) -> ImpBatchImport:
    for k, v in data.items():
        setattr(batch, k, v)
    db.flush()
    return batch


def update_batch_item(db: Session, item: ImpBatchItem, data: dict) -> ImpBatchItem:
    for k, v in data.items():
        setattr(item, k, v)
    db.flush()
    return item


def count_documentos(db: Session, tenant_id: UUID) -> dict:
    """Return counts by estado for dashboard."""
    rows = db.execute(
        select(ImpDocumento.estado, func.count(ImpDocumento.id))
        .where(ImpDocumento.tenant_id == tenant_id)
        .group_by(ImpDocumento.estado)
    ).all()
    return dict(rows)


def count_batch_item_statuses(db: Session, batch_id: UUID) -> dict[str, int]:
    rows = db.execute(
        select(ImpBatchItem.estado, func.count(ImpBatchItem.id))
        .where(ImpBatchItem.batch_id == batch_id)
        .group_by(ImpBatchItem.estado)
    ).all()
    return {str(estado): int(count) for estado, count in rows}


def summarize_batch(db: Session, batch: ImpBatchImport) -> dict:
    counts = count_batch_item_statuses(db, batch.id)
    total_items = int(batch.total_items or sum(counts.values()) or 0)
    pending_items = counts.get("PENDING", 0)
    processing_items = counts.get("PROCESSING", 0)
    review_items = counts.get("REVIEW", 0)
    confirmed_items = counts.get("CONFIRMED", 0)
    failed_items = counts.get("FAILED", 0) + counts.get("REJECTED", 0)
    completed_items = review_items + confirmed_items + failed_items

    if total_items <= 0:
        estado = "PENDING"
    elif pending_items > 0 or processing_items > 0:
        estado = "PROCESSING"
    elif failed_items >= total_items:
        estado = "FAILED"
    elif failed_items > 0:
        estado = "PARTIAL"
    else:
        estado = "COMPLETED"

    progress_pct = int(round((completed_items / total_items) * 100)) if total_items > 0 else 0
    return {
        "id": batch.id,
        "estado": estado,
        "total_items": total_items,
        "pending_items": pending_items,
        "processing_items": processing_items,
        "review_items": review_items,
        "confirmed_items": confirmed_items,
        "failed_items": failed_items,
        "progress_pct": progress_pct,
        "created_at": batch.created_at,
        "updated_at": batch.updated_at,
        "completed_at": batch.completed_at,
    }


def serialize_batch_items(batch: ImpBatchImport) -> list[dict]:
    return [
        {
            "id": item.id,
            "batch_id": item.batch_id,
            "documento_id": item.documento_id,
            "nombre_archivo": item.nombre_archivo,
            "tamanio_bytes": item.tamanio_bytes,
            "estado": item.estado,
            "error_detalle": item.error_detalle,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in sorted(batch.items, key=lambda current: current.orden)
    ]


def serialize_batch_detail(db: Session, batch: ImpBatchImport) -> dict:
    return {
        **summarize_batch(db, batch),
        "items": serialize_batch_items(batch),
    }


def refresh_batch_status(db: Session, batch_id: UUID) -> ImpBatchImport | None:
    batch = db.get(ImpBatchImport, batch_id)
    if batch is None:
        return None

    summary = summarize_batch(db, batch)
    completed_at = batch.completed_at
    if summary["estado"] in {"COMPLETED", "PARTIAL", "FAILED"} and completed_at is None:
        completed_at = datetime.datetime.now(datetime.UTC)
    if summary["estado"] == "PROCESSING":
        completed_at = None
    update_batch(
        db,
        batch,
        {
            "estado": summary["estado"],
            "completed_at": completed_at,
        },
    )
    return batch


def count_documentos_en_estados(db: Session, tenant_id: UUID, estados: tuple[str, ...]) -> int:
    """Cuenta documentos de un tenant en los estados indicados."""
    if not estados:
        return 0
    return int(
        db.scalar(
            select(func.count(ImpDocumento.id)).where(
                and_(
                    ImpDocumento.tenant_id == tenant_id,
                    ImpDocumento.estado.in_(estados),
                )
            )
        )
        or 0
    )


def find_existing_documento(
    db: Session,
    tenant_id: UUID,
    nombre_archivo: str,
    tamanio_bytes: int,
    hash_sha256: str | None = None,
) -> ImpDocumento | None:
    """Busca un documento ya subido para dedupe.

    Prioridad: hash exacto. El nombre del fichero es solo heurística de apoyo
    para registros legacy que no tengan hash persistido.
    """
    status_priority = case(
        (ImpDocumento.estado == "CONFIRMED", 0),
        (ImpDocumento.estado == "REVIEW", 1),
        (ImpDocumento.estado == "PENDING", 2),
        (ImpDocumento.estado == "PROCESSING", 3),
        (ImpDocumento.estado == "FAILED", 4),
        else_=5,
    )

    if hash_sha256:
        doc = db.scalars(
            select(ImpDocumento)
            .where(
                and_(
                    ImpDocumento.tenant_id == tenant_id,
                    ImpDocumento.hash_sha256 == hash_sha256,
                )
            )
            .order_by(status_priority.asc(), ImpDocumento.created_at.desc())
            .limit(1)
        ).first()
        if doc:
            return doc

    return db.scalars(
        select(ImpDocumento)
        .where(
            and_(
                ImpDocumento.tenant_id == tenant_id,
                ImpDocumento.nombre_archivo == nombre_archivo,
                ImpDocumento.tamanio_bytes == tamanio_bytes,
                ImpDocumento.hash_sha256.is_(None),
            )
        )
        .order_by(status_priority.asc(), ImpDocumento.created_at.desc())
        .limit(1)
    ).first()


def find_latest_documento_by_name(
    db: Session,
    tenant_id: UUID,
    nombre_archivo: str,
    *,
    exclude_hash_sha256: str | None = None,
) -> ImpDocumento | None:
    q = select(ImpDocumento).where(
        and_(
            ImpDocumento.tenant_id == tenant_id,
            ImpDocumento.nombre_archivo == nombre_archivo,
        )
    )
    if exclude_hash_sha256:
        q = q.where(
            (ImpDocumento.hash_sha256.is_(None))
            | (ImpDocumento.hash_sha256 != exclude_hash_sha256)
        )
    return db.scalars(q.order_by(ImpDocumento.created_at.desc()).limit(1)).first()


def link_documento_successor(
    db: Session,
    predecessor_id: UUID,
    successor_id: UUID,
    *,
    reason: str = "same_name_new_hash",
) -> None:
    try:
        db.execute(
            text(
                """
                INSERT INTO imp_documento_successor (predecessor_id, successor_id, reason)
                VALUES (:predecessor_id, :successor_id, :reason)
                ON CONFLICT (predecessor_id, successor_id) DO NOTHING
                """
            ),
            {
                "predecessor_id": str(predecessor_id),
                "successor_id": str(successor_id),
                "reason": reason,
            },
        )
        db.flush()
    except Exception:
        # El versionado es complementario; no debe romper la subida principal.
        return


def touch_batch_items_for_document(
    db: Session,
    documento_id: UUID,
    *,
    estado: str,
    error_detalle: str | None = None,
) -> list[UUID]:
    items = db.scalars(select(ImpBatchItem).where(ImpBatchItem.documento_id == documento_id)).all()
    batch_ids: list[UUID] = []
    for item in items:
        item.estado = estado
        item.error_detalle = error_detalle
        batch_ids.append(item.batch_id)
    db.flush()
    return batch_ids


def add_log(
    db: Session,
    documento_id: UUID,
    accion: str,
    usuario_id: str | None = None,
    detalle: dict | None = None,
) -> ImpLogCambios:
    log = ImpLogCambios(
        documento_id=documento_id, accion=accion, usuario_id=usuario_id, detalle=detalle
    )
    db.add(log)
    db.flush()
    return log
