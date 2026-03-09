from __future__ import annotations

import asyncio
import hashlib
import logging
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from . import crud
from .ocr_service import detect_file_type

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
    staged_uploads: list[tuple[str, bytes, int, str, str]] = []
    existing_matches: list[tuple[object, str, int, str]] = []
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
        tipo_archivo = detect_file_type(filename)
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

        if not force:
            existing = crud.find_existing_documento(db, tenant_id, filename, file_size, file_hash)
            if existing and existing.estado in ("PENDING", "PROCESSING", "CONFIRMED", "REVIEW"):
                existing_matches.append((existing, filename, file_size, file_hash))
                continue

        staged_uploads.append((filename, file_bytes, file_size, file_hash, tipo_archivo))

    if not staged_uploads and not existing_matches:
        raise HTTPException(status_code=400, detail="No hay archivos validos para importar.")
    if active_docs + len(staged_uploads) > max_queue_per_tenant:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Cola del importador llena para este tenant: {active_docs} en curso y "
                f"{len(staged_uploads)} nuevos. Limite actual: {max_queue_per_tenant}."
            ),
        )

    batch = crud.create_batch(
        db,
        {
            "tenant_id": tenant_id,
            "usuario_id": user_id,
            "estado": "PENDING",
            "total_items": len(existing_matches) + len(staged_uploads),
            "force_reprocess": force,
            "recipe_snapshot_id": _coerce_uuid(recipe_snapshot_id),
        },
    )
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
        results.append(
            {
                "id": existing.id,
                "batch_id": batch.id,
                "batch_item_id": batch_item.id,
                "estado": existing.estado,
                "nombre_archivo": filename,
            }
        )
    db.commit()

    for offset, (filename, file_bytes, file_size, file_hash, tipo_archivo) in enumerate(
        staged_uploads,
        start=len(existing_matches),
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

        store_payload(str(doc.id), file_bytes)
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
            }
        )

    crud.refresh_batch_status(db, batch.id)
    db.commit()
    return results
