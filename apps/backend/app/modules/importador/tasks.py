"""Celery tasks for the importador module.

Async flow:
  1. POST /importador/run-async stores the uploaded payload and creates
     ImpDocumento(PENDING).
  2. importador.process_document processes the file and updates the document to
     REVIEW or FAILED.
  3. The frontend tracks batch progress until the state becomes terminal.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
from uuid import UUID

logger = logging.getLogger("importador.tasks")

LEGACY_REDIS_KEY_PREFIX = "imp:payload:"


def _payload_dir() -> Path:
    from app.config.settings import settings

    raw_dir = os.getenv("IMPORTADOR_PAYLOAD_DIR") or str(
        Path(settings.UPLOADS_DIR) / "_importador_payloads"
    )
    payload_dir = Path(raw_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)
    return payload_dir


def _payload_path(doc_id: str | UUID) -> Path:
    return _payload_dir() / f"{doc_id}.bin"


def _get_redis():
    """Return a sync Redis client used for legacy payload fallback."""
    import redis  # type: ignore

    url = os.getenv("REDIS_URL") or os.getenv("DEV_REDIS_URL") or "redis://localhost:6379/0"
    return redis.from_url(url, decode_responses=False)


def store_payload(doc_id: str | UUID, file_bytes: bytes) -> None:
    """Store file bytes on local disk to avoid filling Redis memory."""
    payload_path = _payload_path(doc_id)
    tmp_path = payload_path.with_suffix(".tmp")
    tmp_path.write_bytes(file_bytes)
    tmp_path.replace(payload_path)


def load_payload(doc_id: str) -> bytes | None:
    """Load file bytes from disk; fallback to legacy Redis payloads."""
    payload_path = _payload_path(doc_id)
    if payload_path.exists():
        return payload_path.read_bytes()

    try:
        return _get_redis().get(f"{LEGACY_REDIS_KEY_PREFIX}{doc_id}")
    except Exception:
        return None


def delete_payload(doc_id: str) -> None:
    """Delete temporary payloads from disk and clear legacy Redis payloads."""
    try:
        _payload_path(doc_id).unlink(missing_ok=True)
    except Exception:
        logger.warning("No se pudo eliminar payload local de %s", doc_id, exc_info=True)

    try:
        _get_redis().delete(f"{LEGACY_REDIS_KEY_PREFIX}{doc_id}")
    except Exception:
        pass


def publish_batch_update(db, batch_id: UUID) -> None:
    from app.modules.importador import crud

    batch = crud.get_batch_any_tenant(db, batch_id)
    if batch is None:
        return

    payload = crud.serialize_batch_detail(db, batch)
    try:
        _get_redis().publish(f"imp:batch:{batch_id}", json.dumps(_json_safe(payload)))
    except Exception as exc:
        logger.warning("No se pudo publicar batch %s: %s", batch_id, exc)


def _json_safe(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


async def _run_processing(
    doc_id: UUID,
    tenant_id: UUID,
    user_id: str | None,
    file_bytes: bytes,
    filename: str,
    tipo_archivo: str,
    recipe_snapshot_id: str | None = None,
    force: bool = False,
) -> None:
    """Run OCR + AI classification + field extraction and update ImpDocumento."""
    from app.config.database import SessionLocal
    from app.modules.importador import crud
    from app.modules.importador.ai_classifier import CONFIDENCE_THRESHOLD, analyze_document
    from app.modules.importador.auto_recipe import (
        get_snapshot_learning,
        get_snapshot_learning_version,
        remember_snapshot_learning,
        resolve_auto_recipe,
        resolve_auto_recipe_from_text,
    )
    from app.modules.importador.canonical_document import build_document_projection
    from app.modules.importador.field_alias_loader import get_canonical_fields, get_field_aliases
    from app.modules.importador.ocr_service import extract_text_from_file
    from app.modules.importador.runtime_config import load_doc_type_patterns

    with SessionLocal() as db:
        # El worker Celery no tiene request HTTP; hay que propagar el contexto de tenant
        # manualmente para que el evento after_begin aplique los GUCs de RLS correctamente.
        from sqlalchemy import text as _text

        # El worker Celery no tiene request HTTP; hay que propagar el contexto de tenant
        # manualmente para que el evento after_begin aplique los GUCs de RLS correctamente.
        db.info["tenant_id"] = str(tenant_id)
        db.info["user_id"] = str(user_id) if user_id else None
        db.info["bypass_rls"] = True  # worker de confianza; no es una sesión de usuario
        db.execute(_text("SELECT 1"))  # dispara after_begin con los GUCs correctos

        from app.models.importador import ImpDocumento

        doc = db.query(ImpDocumento).filter(ImpDocumento.id == doc_id).first()
        if doc is None:
            logger.error("Documento %s no encontrado en BD", doc_id)
            return

        crud.update_documento(db, doc, {"estado": "PROCESSING"})
        for batch_id in crud.touch_batch_items_for_document(db, doc.id, estado="PROCESSING"):
            crud.refresh_batch_status(db, batch_id)
            publish_batch_update(db, batch_id)
        db.commit()

        try:
            extraction = await extract_text_from_file(file_bytes, filename)
            text = extraction.get("text", "")
            structured = extraction.get("structured_data")
            sheet_profiles = extraction.get("sheet_profiles")

            has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)

            headers_norm: list[str] = []
            headers_display: list[str] = []
            if has_structured:
                for prof in sheet_profiles.values():
                    headers_norm = prof.get("headers_norm") or []
                    headers_display = prof.get("headers") or headers_norm
                    break

            resolved_snapshot_id = None
            explicit_recipe_context = bool(recipe_snapshot_id)
            if sheet_profiles:
                _, resolved_snapshot_id, _, _, _ = resolve_auto_recipe(
                    db, tenant_id, sheet_profiles, user_id
                )
            if recipe_snapshot_id:
                resolved_snapshot_id = recipe_snapshot_id

            if has_structured:
                sample_lines = [f"Columnas: {headers_display}"]
                for row in structured[:5] if isinstance(structured, list) else []:
                    if isinstance(row, dict):
                        sample_lines.append(
                            str({k: v for k, v in list(row.items())[:8] if not k.startswith("_")})
                        )
                llm_content = "\n".join(sample_lines)
            else:
                llm_content = text[:6000] if text else ""
            vision_image_bytes = extraction.get("vision_image_bytes")
            if not isinstance(vision_image_bytes, (bytes, bytearray)):
                vision_image_bytes = file_bytes if tipo_archivo in ("JPG", "PNG", "IMG") else None

            recipe_snapshot = None
            recipe_config = {}
            cached_analysis = None
            if resolved_snapshot_id:
                from app.modules.importador import recipe_crud

                recipe_snapshot = recipe_crud.get_snapshot(db, UUID(str(resolved_snapshot_id)))
                if recipe_snapshot and isinstance(recipe_snapshot.content_json, dict):
                    recipe_config = {
                        "prompt_system": recipe_snapshot.content_json.get("prompt_system"),
                        "prompt_user": recipe_snapshot.content_json.get("prompt_user"),
                        "model": recipe_snapshot.content_json.get("model"),
                        "field_descriptions": recipe_snapshot.content_json.get(
                            "field_descriptions"
                        ),
                    }
                if has_structured:
                    cached_analysis = get_snapshot_learning(
                        recipe_snapshot,
                        structured_only=True,
                    )

            if cached_analysis:
                analysis = {
                    **cached_analysis,
                    "fields": {},
                    "is_table": True,
                    "columns": [],
                    "model_used": "snapshot-cache",
                    "prompt_sent": "",
                    "raw_response": "snapshot-cache",
                }
            else:
                _canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
                analysis = await analyze_document(
                    llm_content,
                    filename,
                    extraction.get("format", tipo_archivo),
                    has_structured_rows=has_structured,
                    recipe_config=recipe_config,
                    image_bytes=bytes(vision_image_bytes) if vision_image_bytes else None,
                    fallback_patterns=load_doc_type_patterns(db),
                    canonical_fields=_canonical_fields,
                )

            tipo_doc = analysis.get("doc_type", "OTHER")
            confianza = float(analysis.get("confidence", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD

            if has_structured and recipe_snapshot:
                remember_snapshot_learning(
                    db,
                    recipe_snapshot,
                    {
                        "doc_type": tipo_doc,
                        "confidence": confianza,
                        "reasoning": analysis.get("reasoning", ""),
                    },
                    structured_only=True,
                )

            crud.add_log(
                db,
                doc.id,
                "CLASSIFY",
                user_id,
                {
                    "tipo_documento": tipo_doc,
                    "confianza": confianza,
                    "razonamiento": analysis.get("reasoning", ""),
                    "model_used": analysis.get("model_used"),
                },
            )

            if has_structured:
                sheet_used_str = extraction.get("sheet_used")
                sheet_metadata_raw = extraction.get("sheet_metadata") or {}
                filas_por_hoja_raw: dict[str, list] = {}
                for row in structured or []:
                    if isinstance(row, dict):
                        sheet_name = str(row.get("_sheet") or sheet_used_str or "")
                        if sheet_name:
                            filas_por_hoja_raw.setdefault(sheet_name, []).append(row)
                datos_extraidos = {
                    "filas": structured[:200],
                    "total_filas": len(structured),
                    "columnas": headers_display or headers_norm,
                    "columnas_norm": headers_norm,
                    "filas_por_hoja": filas_por_hoja_raw,
                    "metadata_por_hoja": sheet_metadata_raw,
                    "sheet_usada": sheet_used_str,
                }
            else:
                datos_extraidos = analysis.get("fields") or {}
                auto_recipe_created = False
                if tipo_doc != "OTHER" and not explicit_recipe_context:
                    auto_recipe_config, post_snapshot_id, _, auto_recipe_created, _ = (
                        resolve_auto_recipe_from_text(
                            db,
                            tenant_id,
                            tipo_doc,
                            datos_extraidos,
                            extraction.get("format", tipo_archivo),
                            user_id,
                            force_new=force,
                        )
                    )
                    if post_snapshot_id:
                        resolved_snapshot_id = post_snapshot_id
                    if auto_recipe_config and not auto_recipe_created:
                        rerun_analysis = await analyze_document(
                            llm_content,
                            filename,
                            extraction.get("format", tipo_archivo),
                            has_structured_rows=False,
                            recipe_config=auto_recipe_config,
                            image_bytes=(bytes(vision_image_bytes) if vision_image_bytes else None),
                            fallback_patterns=load_doc_type_patterns(db),
                            canonical_fields=_canonical_fields,
                        )
                        rerun_doc_type = str(rerun_analysis.get("doc_type", tipo_doc) or tipo_doc)
                        rerun_confidence = float(
                            rerun_analysis.get("confidence", confianza or 0.0) or 0.0
                        )
                        rerun_fields = rerun_analysis.get("fields") or {}
                        if isinstance(rerun_fields, dict) and rerun_fields:
                            analysis = rerun_analysis
                            tipo_doc = rerun_doc_type
                            confianza = rerun_confidence
                            requiere_revision = confianza < CONFIDENCE_THRESHOLD
                            datos_extraidos = rerun_fields
                            recipe_config = auto_recipe_config

            crud.add_log(
                db,
                doc.id,
                "EXTRACT",
                user_id,
                {
                    "campos_extraidos": (
                        list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
                    )
                },
            )

            datos_extraidos = (
                _json_safe(datos_extraidos)
                if isinstance(datos_extraidos, (dict, list))
                else datos_extraidos
            )
            sheet_profiles = (
                _json_safe(sheet_profiles)
                if isinstance(sheet_profiles, (dict, list))
                else sheet_profiles
            )
            current_snapshot = recipe_snapshot
            if current_snapshot is None and resolved_snapshot_id:
                from app.modules.importador import recipe_crud as _recipe_crud

                current_snapshot = _recipe_crud.get_snapshot(db, UUID(str(resolved_snapshot_id)))
            learning_version_applied = get_snapshot_learning_version(current_snapshot)
            _field_aliases = get_field_aliases(db, tenant_id=tenant_id)
            _canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
            canonical_document, projection = build_document_projection(
                datos_extraidos if isinstance(datos_extraidos, dict) else {},
                doc_type=tipo_doc,
                source_format=extraction.get("format", tipo_archivo),
                field_aliases=_field_aliases,
                canonical_fields=_canonical_fields,
            )
            model_used = analysis.get("model_used") or "unknown"
            raw_ai_json = _json_safe(
                {
                    "run": {
                        "recipe_resolution": {
                            "recipe_snapshot_id": (
                                str(resolved_snapshot_id) if resolved_snapshot_id else None
                            ),
                            "learning_version_applied": learning_version_applied,
                        },
                        "learning_version_applied": learning_version_applied,
                        "model": model_used,
                    },
                    "analysis": {
                        "prompt": analysis.get("prompt_sent", ""),
                        "raw_response": analysis.get("raw_response", ""),
                        "parsed": {
                            "tipo_documento": tipo_doc,
                            "confianza": confianza,
                            "razonamiento": analysis.get("reasoning", ""),
                        },
                        "campos_extraidos": (
                            list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
                        ),
                    },
                    "canonical_document": canonical_document,
                }
            )

            crud.update_documento(
                db,
                doc,
                {
                    "texto_ocr": text[:50000],
                    "tipo_documento_detectado": tipo_doc,
                    "confianza_clasificacion": confianza,
                    "requiere_revision": requiere_revision,
                    "datos_extraidos": datos_extraidos,
                    "estado": "REVIEW",
                    **projection,
                    "fingerprint_json": sheet_profiles,
                    "sheet_profiles_json": sheet_profiles,
                    "llm_model": model_used,
                    "raw_ai_json": raw_ai_json,
                    "recipe_snapshot_id": resolved_snapshot_id,
                },
            )

            # Poblar staging lines para habilitar el reprocesado iterativo.
            if isinstance(datos_extraidos, dict):
                from .services.iteration_service import upsert_staging_lines_from_extraction
                _n = upsert_staging_lines_from_extraction(db, doc.id, doc.tenant_id, datos_extraidos)
                if _n:
                    logger.info("Staging: %d líneas creadas para doc %s", _n, doc.id)

            for batch_id in crud.touch_batch_items_for_document(db, doc.id, estado="REVIEW"):
                crud.refresh_batch_status(db, batch_id)
                publish_batch_update(db, batch_id)
            db.commit()
            logger.info("Documento %s procesado correctamente -> REVIEW", doc_id)

        except Exception as exc:
            logger.error("Error procesando documento %s: %s", doc_id, exc, exc_info=True)
            crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": str(exc)})
            crud.add_log(db, doc.id, "EXTRACT", user_id, {"error": str(exc)})
            for batch_id in crud.touch_batch_items_for_document(
                db,
                doc.id,
                estado="FAILED",
                error_detalle=str(exc),
            ):
                crud.refresh_batch_status(db, batch_id)
                publish_batch_update(db, batch_id)
            db.commit()


def _make_task():
    """Register the Celery task lazily to avoid startup failures."""
    try:
        from celery_app import celery_app  # type: ignore
    except Exception:
        return None

    @celery_app.task(
        name="importador.process_document",
        bind=True,
        queue="importador",
        max_retries=2,
        default_retry_delay=30,
        time_limit=420,
        soft_time_limit=390,
        acks_late=True,
        reject_on_worker_lost=True,
    )
    def process_document(
        self,
        doc_id: str,
        tenant_id: str,
        user_id: str | None,
        filename: str,
        tipo_archivo: str,
        recipe_snapshot_id: str | None = None,
        force: bool = False,
    ) -> dict:
        logger.info("Iniciando procesamiento async de documento %s (%s)", doc_id, filename)

        file_bytes = load_payload(doc_id)
        if not file_bytes:
            msg = f"Payload no encontrado para doc {doc_id}; puede haber expirado"
            logger.error(msg)
            try:
                from app.config.database import SessionLocal
                from app.models.importador import ImpDocumento
                from app.modules.importador import crud

                with SessionLocal() as db:
                    from sqlalchemy import text as _text

                    db.info["tenant_id"] = tenant_id
                    db.info["bypass_rls"] = True
                    db.execute(_text("SELECT 1"))
                    doc = db.query(ImpDocumento).filter(ImpDocumento.id == UUID(doc_id)).first()
                    if doc:
                        crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": msg})
                        for batch_id in crud.touch_batch_items_for_document(
                            db,
                            doc.id,
                            estado="FAILED",
                            error_detalle=msg,
                        ):
                            crud.refresh_batch_status(db, batch_id)
                            publish_batch_update(db, batch_id)
                        db.commit()
            except Exception as exc:
                logger.error("No se pudo marcar FAILED doc %s: %s", doc_id, exc)
            return {"ok": False, "error": msg}

        try:
            asyncio.run(
                _run_processing(
                    doc_id=UUID(doc_id),
                    tenant_id=UUID(tenant_id),
                    user_id=user_id,
                    file_bytes=file_bytes,
                    filename=filename,
                    tipo_archivo=tipo_archivo,
                    recipe_snapshot_id=recipe_snapshot_id,
                    force=force,
                )
            )
        except Exception as exc:
            logger.error("Task fallo para doc %s: %s", doc_id, exc, exc_info=True)
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                return {"ok": False, "error": str(exc)}
        finally:
            delete_payload(doc_id)

        return {"ok": True, "doc_id": doc_id}

    return process_document


process_document_task = _make_task()
