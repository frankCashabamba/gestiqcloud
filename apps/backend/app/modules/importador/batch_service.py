from __future__ import annotations

import asyncio
import hashlib
import logging
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models.importador import ImpBatchImport, ImpBatchItem

from . import crud
from .ocr_service import detect_file_type
from .snapshot_learning import bootstrap_learning_from_existing_document

logger = logging.getLogger(__name__)


def _coerce_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _should_skip_import_file(filename: str) -> bool:
    normalized = (filename or "").strip()
    return (
        not normalized
        or normalized.startswith("~$")
        or normalized.lower() in {"thumbs.db", ".ds_store"}
    )


def _env_int(name: str, default: int) -> int:
    import os

    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _batch_tracking_schema_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "importador_batch_tracking_schema_missing:"
            "apply_ops_migration=2026-03-09_000_importer_batch_tracking"
        ),
    )


def _is_missing_batch_tracking_tables(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "imp_batch_import" in msg
        or "imp_batch_item" in msg
        or "undefinedtable" in msg
        or "does not exist" in msg
        or "no existe la relacion" in msg
        or "no existe la relación" in msg
    )


def _ensure_batch_tracking_storage(db: Session) -> bool:
    cached = db.info.get("importador_batch_tracking_ready")
    if cached is not None:
        return bool(cached)

    available = False
    try:
        inspector = inspect(db.bind)
        schema = "public" if getattr(db.bind.dialect, "name", "") == "postgresql" else None
        has_batch = inspector.has_table("imp_batch_import", schema=schema)
        has_item = inspector.has_table("imp_batch_item", schema=schema)

        if not has_batch or not has_item:
            dependencies = {
                "tenants": inspector.has_table("tenants", schema=schema),
                "imp_documento": inspector.has_table("imp_documento", schema=schema),
                "icu_recipe_snapshot": inspector.has_table("icu_recipe_snapshot", schema=schema),
            }
            if all(dependencies.values()):
                if not has_batch:
                    ImpBatchImport.__table__.create(bind=db.bind, checkfirst=True)
                if not has_item:
                    ImpBatchItem.__table__.create(bind=db.bind, checkfirst=True)

                inspector = inspect(db.bind)
                has_batch = inspector.has_table("imp_batch_import", schema=schema)
                has_item = inspector.has_table("imp_batch_item", schema=schema)
                if has_batch and has_item:
                    logger.warning(
                        "Auto-created missing importador batch tracking tables. "
                        "Apply SQL migration 2026-03-09_000_importer_batch_tracking "
                        "to keep schema history in sync."
                    )
            else:
                logger.warning(
                    "Importador batch tracking tables are missing and cannot be auto-created "
                    "(dependencies=%s)",
                    dependencies,
                )

        available = has_batch and has_item
    except Exception:
        logger.exception("Could not ensure importador batch tracking storage")
        db.rollback()
        available = False

    db.info["importador_batch_tracking_ready"] = available
    return available


async def enqueue_async_batch(
    *,
    files: list[UploadFile],
    tenant_id: UUID,
    user_id: str,
    force: bool,
    recipe_snapshot_id: str | None,
    db: Session,
) -> list[dict]:
    from .tasks import process_document_task, store_payload

    max_files_per_request = _env_int("IMPORTADOR_MAX_FILES_PER_REQUEST", 100)
    max_queue_per_tenant = _env_int("IMPORTADOR_MAX_QUEUE_PER_TENANT", 100)
    max_file_size_mb = _env_int("IMPORTS_MAX_FILE_SIZE_MB", 16)
    max_batch_size_mb = _env_int("IMPORTS_MAX_UPLOAD_MB", 50)
    max_file_size_bytes = max(1, max_file_size_mb) * 1024 * 1024
    max_batch_size_bytes = max(1, max_batch_size_mb) * 1024 * 1024

    if len(files) > max_files_per_request:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Demasiados archivos en una sola subida ({len(files)}). "
                f"Limite actual: {max_files_per_request}."
            ),
        )

    active_docs = crud.count_documentos_en_estados(db, tenant_id, ("PENDING", "PROCESSING"))
    staged_uploads: list[tuple[str, bytes, int, str, str, object | None]] = []
    existing_matches: list[tuple[object, str, int, str]] = []
    rerun_existing: list[tuple[object, str, bytes, int, str, str]] = []
    batch_size_bytes = 0

    for file in files:
        filename = (file.filename or "unknown").strip()
        if _should_skip_import_file(filename):
            logger.info("Ignorando archivo temporal/no valido en importador: %s", filename)
            continue

        file_bytes = await file.read()
        file_size = len(file_bytes)
        if file_size <= 0:
            logger.info("Ignorando archivo vacio en importador: %s", filename)
            continue
        tipo_archivo = detect_file_type(filename, db)
        # Excel/XLS: sin límite de tamaño — openpyxl read_only ignora imágenes
        # embebidas; los row-limits internos acotan la memoria real usada.
        _es_excel = tipo_archivo in ("XLSX", "XLS")
        if not _es_excel and file_size > max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Archivo '{filename}' excede el limite de {max_file_size_mb} MB "
                    f"({round(file_size / (1024 * 1024), 1)} MB)."
                ),
            )

        if not _es_excel:
            batch_size_bytes += file_size
            if batch_size_bytes > max_batch_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"El lote excede el limite de {max_batch_size_mb} MB. "
                        "Divide la importacion en bloques mas pequenos."
                    ),
                )
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = (
            None
            if force and not file_hash
            else crud.find_existing_documento(db, tenant_id, filename, file_size, file_hash)
        )
        exact_hash_match = bool(existing and existing.hash_sha256 == file_hash)
        if existing:
            if existing.estado in ("CONFIRMED", "REVIEW"):
                bootstrap_learning_from_existing_document(db, existing, user_id)

            if existing.estado in ("PENDING", "PROCESSING"):
                existing_matches.append((existing, filename, file_size, file_hash))
                continue

            if existing.estado in ("CONFIRMED", "REVIEW") and not force:
                existing_matches.append((existing, filename, file_size, file_hash))
                continue

            if exact_hash_match and existing.estado in ("FAILED", "REVIEW", "CONFIRMED"):
                rerun_existing.append(
                    (existing, filename, file_bytes, file_size, file_hash, tipo_archivo)
                )
                continue

        predecessor = crud.find_latest_documento_by_name(
            db,
            tenant_id,
            filename,
            exclude_hash_sha256=file_hash,
        )
        staged_uploads.append(
            (filename, file_bytes, file_size, file_hash, tipo_archivo, predecessor)
        )

    if not staged_uploads and not existing_matches and not rerun_existing:
        raise HTTPException(status_code=400, detail="No hay archivos validos para importar.")
    queued_docs = len(staged_uploads) + len(rerun_existing)
    if active_docs + queued_docs > max_queue_per_tenant:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Cola del importador llena para este tenant: {active_docs} en curso y "
                f"{queued_docs} nuevos. Limite actual: {max_queue_per_tenant}."
            ),
        )

    if not _ensure_batch_tracking_storage(db):
        raise _batch_tracking_schema_error()

    batch_payload = {
        "tenant_id": tenant_id,
        "usuario_id": user_id,
        "estado": "PENDING",
        "total_items": len(existing_matches) + len(staged_uploads) + len(rerun_existing),
        "force_reprocess": force,
        "recipe_snapshot_id": _coerce_uuid(recipe_snapshot_id),
    }
    try:
        batch = crud.create_batch(db, batch_payload)
    except ProgrammingError as exc:
        db.rollback()
        db.info.pop("importador_batch_tracking_ready", None)
        if _is_missing_batch_tracking_tables(exc) and _ensure_batch_tracking_storage(db):
            batch = crud.create_batch(db, batch_payload)
        else:
            raise _batch_tracking_schema_error() from exc
    db.commit()

    results: list[dict] = []

    for index, (existing, filename, file_size, file_hash) in enumerate(existing_matches):
        batch_item = crud.create_batch_item(
            db,
            {
                "batch_id": batch.id,
                "tenant_id": tenant_id,
                "documento_id": existing.id,
                "nombre_archivo": filename,
                "tamanio_bytes": file_size,
                "hash_sha256": file_hash,
                "orden": index,
                "estado": existing.estado,
                "error_detalle": getattr(existing, "error_detalle", None),
            },
        )
        crud.add_log(
            db,
            existing.id,
            "SKIP_DUPLICATE",
            user_id,
            {
                "filename": filename,
                "size": file_size,
                "mode": "async",
                "reason": "same hash_or_name",
            },
        )
        results.append(
            {
                "id": existing.id,
                "batch_id": batch.id,
                "batch_item_id": batch_item.id,
                "estado": existing.estado,
                "nombre_archivo": filename,
                "action": "REUSED",
                "message": (
                    "Documento ya existente; se reutilizo el mismo registro. "
                    "Usa reimportacion limpia para reprocesarlo."
                ),
            }
        )
    db.commit()

    rerun_start = len(existing_matches)
    for offset, (existing, filename, file_bytes, file_size, file_hash, tipo_archivo) in enumerate(
        rerun_existing,
        start=rerun_start,
    ):
        crud.reset_documento_for_reprocess(
            db,
            existing,
            estado="PENDING",
            clear_recipe_snapshot=True,
        )
        batch_item = crud.create_batch_item(
            db,
            {
                "batch_id": batch.id,
                "tenant_id": tenant_id,
                "documento_id": existing.id,
                "nombre_archivo": filename,
                "tamanio_bytes": file_size,
                "hash_sha256": file_hash,
                "orden": offset,
                "estado": "PENDING",
            },
        )
        crud.add_log(
            db,
            existing.id,
            "REPROCESS",
            user_id,
            {"filename": filename, "size": file_size, "mode": "async", "batch_id": str(batch.id)},
        )
        db.commit()

        await asyncio.to_thread(store_payload, str(existing.id), file_bytes)
        if process_document_task:
            process_document_task.delay(
                doc_id=str(existing.id),
                tenant_id=str(tenant_id),
                user_id=user_id,
                filename=filename,
                tipo_archivo=tipo_archivo,
                recipe_snapshot_id=str(recipe_snapshot_id) if recipe_snapshot_id else None,
                force=force,
            )
        else:
            logger.warning("Celery no disponible; dejando documento %s en PENDING", existing.id)

        results.append(
            {
                "id": existing.id,
                "batch_id": batch.id,
                "batch_item_id": batch_item.id,
                "estado": "PENDING",
                "nombre_archivo": filename,
                "action": "REPROCESS",
                "message": "Se reproceso el mismo documento sobre el registro existente.",
            }
        )

    for offset, (
        filename,
        file_bytes,
        file_size,
        file_hash,
        tipo_archivo,
        predecessor,
    ) in enumerate(
        staged_uploads,
        start=rerun_start + len(rerun_existing),
    ):
        doc = crud.create_documento(
            db,
            {
                "tenant_id": tenant_id,
                "nombre_archivo": filename,
                "tipo_archivo": tipo_archivo,
                "tamanio_bytes": file_size,
                "hash_sha256": file_hash,
                "estado": "PENDING",
                "usuario_id": user_id,
            },
        )
        if predecessor and predecessor.id != doc.id:
            crud.link_documento_successor(db, predecessor.id, doc.id)
        batch_item = crud.create_batch_item(
            db,
            {
                "batch_id": batch.id,
                "tenant_id": tenant_id,
                "documento_id": doc.id,
                "nombre_archivo": filename,
                "tamanio_bytes": file_size,
                "hash_sha256": file_hash,
                "orden": offset,
                "estado": "PENDING",
            },
        )
        crud.add_log(
            db,
            doc.id,
            "UPLOAD",
            user_id,
            {"filename": filename, "size": file_size, "mode": "async", "batch_id": str(batch.id)},
        )
        db.commit()

        await asyncio.to_thread(store_payload, str(doc.id), file_bytes)
        if process_document_task:
            process_document_task.delay(
                doc_id=str(doc.id),
                tenant_id=str(tenant_id),
                user_id=user_id,
                filename=filename,
                tipo_archivo=tipo_archivo,
                recipe_snapshot_id=recipe_snapshot_id,
                force=force,
            )
        else:
            logger.warning("Celery no disponible, procesando %s sincronicamente", filename)
            from .tasks import _run_processing

            try:
                asyncio.create_task(
                    _run_processing(
                        doc_id=UUID(str(doc.id)),
                        tenant_id=UUID(str(tenant_id)),
                        user_id=user_id,
                        file_bytes=file_bytes,
                        filename=filename,
                        tipo_archivo=tipo_archivo,
                        recipe_snapshot_id=recipe_snapshot_id,
                        force=force,
                    )
                )
            except Exception:
                pass

        results.append(
            {
                "id": doc.id,
                "batch_id": batch.id,
                "batch_item_id": batch_item.id,
                "estado": "PENDING",
                "nombre_archivo": filename,
                "action": "CREATED",
                "message": "Se creo un nuevo documento para esta importacion.",
            }
        )

    crud.refresh_batch_status(db, batch.id)
    db.commit()
    return results
