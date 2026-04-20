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
from .auto_recipe import should_reprocess_existing_document
from .ocr_service import detect_file_type, iter_zip_entries
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


def _build_reprocess_context(
    existing, *, reprocess_mode: str, rerun_reason: str
) -> dict[str, object]:
    raw_data = getattr(existing, "datos_extraidos", None)
    field_count = 0
    if isinstance(raw_data, dict):
        field_count = len(
            [
                key
                for key, value in raw_data.items()
                if not str(key).startswith("_") and value not in (None, "", [], {})
            ]
        )
    field_keys = []
    if isinstance(raw_data, dict):
        field_keys = sorted(
            str(key)
            for key, value in raw_data.items()
            if not str(key).startswith("_") and value not in (None, "", [], {})
        )
    routing = getattr(existing, "routing_decision", None)
    missing_fields = getattr(routing, "missing_fields", None) or []
    previous_result = {
        "tipo_documento_detectado": getattr(existing, "tipo_documento_detectado", None),
        "confianza_clasificacion": getattr(existing, "confianza_clasificacion", None),
        "requiere_revision": getattr(existing, "requiere_revision", None),
        "recipe_snapshot_id": getattr(existing, "recipe_snapshot_id", None),
        "llm_model": getattr(existing, "llm_model", None),
        "field_count": field_count,
        "field_keys": field_keys,
        "rerun_reason": rerun_reason,
    }
    return {
        "mode": reprocess_mode,
        "previous_result": previous_result,
        "missing_fields": [str(field).strip() for field in missing_fields if str(field).strip()],
    }


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
    reprocess_mode: str = "fast",
    db: Session,
) -> list[dict]:
    from .tasks import decide_initial_lane, process_document_task, store_payload

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
    staged_uploads: list[dict[str, object]] = []
    existing_matches: list[dict[str, object]] = []
    rerun_existing: list[dict[str, object]] = []
    failed_uploads: list[dict[str, object]] = []
    batch_size_bytes = 0
    request_hash_map: dict[str, tuple[str, int]] = {}
    bucket_map = {
        "staged": staged_uploads,
        "existing": existing_matches,
        "rerun": rerun_existing,
    }
    order_counter = 0

    def _alias_payload(
        filename: str, file_size: int, file_hash: str, order: int
    ) -> dict[str, object]:
        return {
            "filename": filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "order": order,
        }

    def _append_request_duplicate(file_hash: str, alias: dict[str, object]) -> bool:
        bucket_info = request_hash_map.get(file_hash)
        if not bucket_info:
            return False
        bucket_name, index = bucket_info
        bucket_map[bucket_name][index].setdefault("aliases", []).append(alias)
        return True

    def _register_request_hash(file_hash: str, bucket_name: str, index: int) -> None:
        request_hash_map[file_hash] = (bucket_name, index)

    def _iter_incoming_entries(
        filename: str,
        file_bytes: bytes,
        tipo_archivo: str,
        order: int,
    ) -> list[tuple[str, bytes, str, int]]:
        if tipo_archivo != "ZIP":
            return [(filename, file_bytes, tipo_archivo, order)]
        entries = list(iter_zip_entries(file_bytes, db=db))
        if not entries:
            failed_uploads.append(
                {
                    "filename": filename,
                    "file_size": len(file_bytes),
                    "tipo_archivo": tipo_archivo,
                    "order": order,
                    "error_detalle": "ZIP vacio o sin ficheros soportados",
                }
            )
            return []
        return [
            (
                f"{filename}::{inner_name}",
                inner_bytes,
                detect_file_type(inner_name, db),
                order + index,
            )
            for index, (inner_name, inner_bytes) in enumerate(entries)
        ]

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
        _es_excel = tipo_archivo in ("XLSX", "XLS")
        if not _es_excel and file_size > max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Archivo '{filename}' excede el limite de {max_file_size_mb} MB "
                    f"({round(file_size / (1024 * 1024), 1)} MB)."
                ),
            )

        incoming_entries = _iter_incoming_entries(filename, file_bytes, tipo_archivo, order_counter)
        order_counter += max(1, len(incoming_entries))

        for entry_filename, entry_bytes, entry_tipo_archivo, entry_order in incoming_entries:
            entry_size = len(entry_bytes)
            entry_is_excel = entry_tipo_archivo in ("XLSX", "XLS")
            if not entry_is_excel:
                batch_size_bytes += entry_size
                if batch_size_bytes > max_batch_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"El lote excede el limite de {max_batch_size_mb} MB. "
                            "Divide la importacion en bloques mas pequenos."
                        ),
                    )

            entry_hash = hashlib.sha256(entry_bytes).hexdigest()
            if _append_request_duplicate(
                entry_hash,
                _alias_payload(entry_filename, entry_size, entry_hash, entry_order),
            ):
                continue

            existing = (
                None
                if force and not entry_hash
                else crud.find_existing_documento(
                    db,
                    tenant_id,
                    entry_filename,
                    entry_size,
                    entry_hash,
                    usuario_id=user_id,
                )
            )
            exact_hash_match = bool(existing and existing.hash_sha256 == entry_hash)
            if existing:
                if (
                    isinstance(getattr(existing, "datos_confirmados", None), dict)
                    and existing.datos_confirmados
                ):
                    bootstrap_learning_from_existing_document(db, existing, user_id)
                learning_reprocess_needed = bool(
                    exact_hash_match
                    and existing.estado in ("CONFIRMED", "REVIEW")
                    and should_reprocess_existing_document(db, existing)
                )

                if existing.estado in ("PENDING", "PROCESSING"):
                    existing_matches.append(
                        {
                            "existing": existing,
                            "filename": entry_filename,
                            "file_size": entry_size,
                            "file_hash": entry_hash,
                            "order": entry_order,
                            "aliases": [],
                        }
                    )
                    _register_request_hash(entry_hash, "existing", len(existing_matches) - 1)
                    continue

                if learning_reprocess_needed and not force:
                    rerun_existing.append(
                        {
                            "existing": existing,
                            "filename": entry_filename,
                            "file_bytes": entry_bytes,
                            "file_size": entry_size,
                            "file_hash": entry_hash,
                            "tipo_archivo": entry_tipo_archivo,
                            "rerun_reason": "learning_update",
                            "order": entry_order,
                            "aliases": [],
                        }
                    )
                    _register_request_hash(entry_hash, "rerun", len(rerun_existing) - 1)
                    continue

                if existing.estado in ("CONFIRMED", "REVIEW") and not force:
                    existing_matches.append(
                        {
                            "existing": existing,
                            "filename": entry_filename,
                            "file_size": entry_size,
                            "file_hash": entry_hash,
                            "order": entry_order,
                            "aliases": [],
                        }
                    )
                    _register_request_hash(entry_hash, "existing", len(existing_matches) - 1)
                    continue

                if exact_hash_match and existing.estado in ("FAILED", "REVIEW", "CONFIRMED"):
                    rerun_existing.append(
                        {
                            "existing": existing,
                            "filename": entry_filename,
                            "file_bytes": entry_bytes,
                            "file_size": entry_size,
                            "file_hash": entry_hash,
                            "tipo_archivo": entry_tipo_archivo,
                            "rerun_reason": "manual",
                            "order": entry_order,
                            "aliases": [],
                        }
                    )
                    _register_request_hash(entry_hash, "rerun", len(rerun_existing) - 1)
                    continue

            predecessor = crud.find_latest_documento_by_name(
                db,
                tenant_id,
                entry_filename,
                exclude_hash_sha256=entry_hash,
                usuario_id=user_id,
            )
            staged_uploads.append(
                {
                    "filename": entry_filename,
                    "file_bytes": entry_bytes,
                    "file_size": entry_size,
                    "file_hash": entry_hash,
                    "tipo_archivo": entry_tipo_archivo,
                    "predecessor": predecessor,
                    "order": entry_order,
                    "aliases": [],
                }
            )
            _register_request_hash(entry_hash, "staged", len(staged_uploads) - 1)

    if not staged_uploads and not existing_matches and not rerun_existing and not failed_uploads:
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

    normalized_reprocess_mode = (
        "deep" if str(reprocess_mode or "").strip().lower() == "deep" else "fast"
    )
    effective_recipe_snapshot_id = (
        None if normalized_reprocess_mode == "deep" else _coerce_uuid(recipe_snapshot_id)
    )

    batch_payload = {
        "tenant_id": tenant_id,
        "usuario_id": user_id,
        "estado": "PENDING",
        "total_items": (
            len(existing_matches)
            + len(staged_uploads)
            + len(rerun_existing)
            + len(failed_uploads)
            + sum(len(item.get("aliases") or []) for item in existing_matches)
            + sum(len(item.get("aliases") or []) for item in staged_uploads)
            + sum(len(item.get("aliases") or []) for item in rerun_existing)
        ),
        "force_reprocess": force,
        "recipe_snapshot_id": effective_recipe_snapshot_id,
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

    def _append_alias_results(
        *,
        document_id,
        estado: str,
        aliases: list[dict[str, object]],
        message: str,
    ) -> None:
        for alias in sorted(aliases, key=lambda current: int(current["order"])):
            batch_item = crud.create_batch_item(
                db,
                {
                    "batch_id": batch.id,
                    "tenant_id": tenant_id,
                    "documento_id": document_id,
                    "nombre_archivo": alias["filename"],
                    "tamanio_bytes": alias["file_size"],
                    "hash_sha256": alias["file_hash"],
                    "orden": alias["order"],
                    "estado": estado,
                },
            )
            crud.add_log(
                db,
                document_id,
                "SKIP_DUPLICATE",
                user_id,
                {
                    "filename": alias["filename"],
                    "size": alias["file_size"],
                    "mode": "async",
                    "reason": "same_hash_same_request",
                },
            )
            results.append(
                {
                    "id": document_id,
                    "batch_id": batch.id,
                    "batch_item_id": batch_item.id,
                    "estado": estado,
                    "nombre_archivo": alias["filename"],
                    "action": "REUSED",
                    "message": message,
                }
            )

    for item in sorted(existing_matches, key=lambda current: int(current["order"])):
        existing = item["existing"]
        filename = str(item["filename"])
        file_size = int(item["file_size"])
        file_hash = str(item["file_hash"])
        batch_item = crud.create_batch_item(
            db,
            {
                "batch_id": batch.id,
                "tenant_id": tenant_id,
                "documento_id": existing.id,
                "nombre_archivo": filename,
                "tamanio_bytes": file_size,
                "hash_sha256": file_hash,
                "orden": item["order"],
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
                    "Documento ya existente; se reutilizo el resultado actual porque no habia aprendizaje nuevo pendiente. "
                    "Usa reimportacion limpia si quieres forzar otro analisis."
                ),
            }
        )
        _append_alias_results(
            document_id=existing.id,
            estado=existing.estado,
            aliases=list(item.get("aliases") or []),
            message="Archivo duplicado dentro de la misma subida; se reutilizo el mismo documento existente.",
        )
    db.commit()

    for item in sorted(rerun_existing, key=lambda current: int(current["order"])):
        existing = item["existing"]
        filename = str(item["filename"])
        file_bytes = bytes(item["file_bytes"])
        file_size = int(item["file_size"])
        file_hash = str(item["file_hash"])
        tipo_archivo = str(item["tipo_archivo"])
        rerun_reason = str(item["rerun_reason"])
        reprocess_context = _build_reprocess_context(
            existing,
            reprocess_mode=normalized_reprocess_mode,
            rerun_reason=rerun_reason,
        )
        preserve_learning_snapshot = (
            rerun_reason == "learning_update"
            and getattr(existing, "recipe_snapshot_id", None)
            and normalized_reprocess_mode != "deep"
        )
        crud.reset_documento_for_reprocess(
            db,
            existing,
            estado="PENDING",
            recipe_snapshot_id=existing.recipe_snapshot_id if preserve_learning_snapshot else None,
            clear_recipe_snapshot=not bool(preserve_learning_snapshot),
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
                "orden": item["order"],
                "estado": "PENDING",
            },
        )
        crud.add_log(
            db,
            existing.id,
            "REPROCESS",
            user_id,
            {
                "filename": filename,
                "size": file_size,
                "mode": "async",
                "batch_id": str(batch.id),
                "reason": rerun_reason,
                "reprocess_mode": normalized_reprocess_mode,
                "deep_reprocess": normalized_reprocess_mode == "deep",
            },
        )
        db.commit()

        await asyncio.to_thread(store_payload, str(existing.id), file_bytes)
        if process_document_task:
            _rerun_snap_id = (
                str(recipe_snapshot_id)
                if recipe_snapshot_id and normalized_reprocess_mode != "deep"
                else None
            )
            _rerun_lane = decide_initial_lane(
                tipo_archivo=tipo_archivo,
                reprocess_mode=normalized_reprocess_mode,
                has_recipe_context=bool(_rerun_snap_id),
            )
            process_document_task.apply_async(
                kwargs={
                    "doc_id": str(existing.id),
                    "tenant_id": str(tenant_id),
                    "user_id": user_id,
                    "filename": filename,
                    "tipo_archivo": tipo_archivo,
                    "recipe_snapshot_id": _rerun_snap_id,
                    "force": force,
                    "reprocess_mode": normalized_reprocess_mode,
                    "reprocess_context": reprocess_context,
                },
                queue=f"importador_{_rerun_lane}",
            )
            logger.info(
                "importador.enqueue rerun doc_id=%s lane=%s queue=importador_%s",
                existing.id,
                _rerun_lane,
                _rerun_lane,
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
                "message": (
                    "Se reanalizo el mismo documento para aplicar aprendizaje confirmado reciente."
                    if rerun_reason == "learning_update"
                    else (
                        "Reprocesado profundo desde cero."
                        if normalized_reprocess_mode == "deep"
                        else "Se reproceso el mismo documento sobre el registro existente."
                    )
                ),
            }
        )
        _append_alias_results(
            document_id=existing.id,
            estado="PENDING",
            aliases=list(item.get("aliases") or []),
            message="Archivo duplicado dentro de la misma subida; se reutilizo el mismo reprocesado ya en cola.",
        )

    for item in sorted(staged_uploads, key=lambda current: int(current["order"])):
        filename = str(item["filename"])
        file_bytes = bytes(item["file_bytes"])
        file_size = int(item["file_size"])
        file_hash = str(item["file_hash"])
        tipo_archivo = str(item["tipo_archivo"])
        predecessor = item.get("predecessor")
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
                "orden": item["order"],
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
            _upload_snap_id = (
                str(effective_recipe_snapshot_id) if effective_recipe_snapshot_id else None
            )
            _upload_lane = decide_initial_lane(
                tipo_archivo=tipo_archivo,
                reprocess_mode=normalized_reprocess_mode,
                has_recipe_context=bool(_upload_snap_id),
            )
            process_document_task.apply_async(
                kwargs={
                    "doc_id": str(doc.id),
                    "tenant_id": str(tenant_id),
                    "user_id": user_id,
                    "filename": filename,
                    "tipo_archivo": tipo_archivo,
                    "recipe_snapshot_id": _upload_snap_id,
                    "force": force,
                    "reprocess_mode": normalized_reprocess_mode,
                    "reprocess_context": {},
                },
                queue=f"importador_{_upload_lane}",
            )
            logger.info(
                "importador.enqueue upload doc_id=%s lane=%s queue=importador_%s",
                doc.id,
                _upload_lane,
                _upload_lane,
            )
        else:
            logger.warning(
                "Celery no disponible; documento %s queda en PENDING sin procesar",
                doc.id,
            )

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
        _append_alias_results(
            document_id=doc.id,
            estado="PENDING",
            aliases=list(item.get("aliases") or []),
            message="Archivo duplicado dentro de la misma subida; se reutilizo el mismo documento en cola.",
        )

    for failed in sorted(failed_uploads, key=lambda current: int(current["order"])):
        doc = crud.create_documento(
            db,
            {
                "tenant_id": tenant_id,
                "nombre_archivo": failed["filename"],
                "tipo_archivo": failed["tipo_archivo"],
                "tamanio_bytes": failed["file_size"],
                "estado": "FAILED",
                "usuario_id": user_id,
                "error_detalle": failed["error_detalle"],
            },
        )
        batch_item = crud.create_batch_item(
            db,
            {
                "batch_id": batch.id,
                "tenant_id": tenant_id,
                "documento_id": doc.id,
                "nombre_archivo": failed["filename"],
                "tamanio_bytes": failed["file_size"],
                "hash_sha256": None,
                "orden": failed["order"],
                "estado": "FAILED",
                "error_detalle": failed["error_detalle"],
            },
        )
        crud.add_log(
            db,
            doc.id,
            "ERROR",
            user_id,
            {"error": failed["error_detalle"], "mode": "async"},
        )
        results.append(
            {
                "id": doc.id,
                "batch_id": batch.id,
                "batch_item_id": batch_item.id,
                "estado": "FAILED",
                "nombre_archivo": failed["filename"],
                "action": "CREATED",
                "message": failed["error_detalle"],
            }
        )

    crud.refresh_batch_status(db, batch.id)
    db.commit()
    return results
