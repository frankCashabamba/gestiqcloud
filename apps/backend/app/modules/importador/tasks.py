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
import json
import logging
import os
import time
from pathlib import Path
from uuid import UUID

from .processing_service import RecipeContext, process_import_document
from .utils import json_safe as _json_safe

logger = logging.getLogger("importador.tasks")

# Formatos visuales: pre-OCR sabemos que necesitan deep lane.
_INITIAL_VISUAL_FORMATS: frozenset[str] = frozenset(
    {
        "JPG",
        "JPEG",
        "PNG",
        "IMG",
        "HEIC",
        "WEBP",
        "IMAGE_OCR",
        "PDF_OCR",
    }
)
# Formatos estructurados: bypass directo sin LLM → fast lane.
_INITIAL_STRUCTURED_FORMATS: frozenset[str] = frozenset(
    {
        "CSV",
        "XML",
        "JSON",
        "XLS",
        "XLSX",
        "EXCEL",
    }
)


def decide_initial_lane(
    *,
    tipo_archivo: str,
    reprocess_mode: str,
    has_recipe_context: bool = False,
) -> str:
    """Decisión de carril pre-OCR para encolado en Celery.

    Usa solo señales disponibles antes del procesamiento (formato, modo,
    contexto de receta). La decisión post-OCR completa ocurre en
    processing_service.decide_processing_lane() dentro de la tarea.

    Returns:
        "fast"  → cola importador_fast  (documentos estructurados o contexto fuerte)
        "deep"  → cola importador_deep  (visual, PDF ambiguo, primera importación)
    """
    if str(reprocess_mode or "").strip().lower() == "deep":
        return "deep"

    tipo = str(tipo_archivo or "").upper()

    if tipo in _INITIAL_VISUAL_FORMATS:
        return "deep"

    # PDF sin contexto de receta → puede ser escaneado, ambiguo → deep
    if tipo == "PDF" and not has_recipe_context:
        return "deep"

    # Estructurados → bypass local sin LLM → fast
    if tipo in _INITIAL_STRUCTURED_FORMATS:
        return "fast"

    # Conservador: cualquier formato desconocido va a deep
    return "deep"


def _payload_dir() -> Path:
    from app.config.settings import settings

    raw_dir = os.getenv("IMPORTADOR_PAYLOAD_DIR")
    payload_dir = (
        Path(raw_dir).expanduser() if raw_dir else settings.uploads_path / "_importador_payloads"
    )
    if not payload_dir.is_absolute():
        payload_dir = settings.uploads_path.parent / payload_dir
    payload_dir.mkdir(parents=True, exist_ok=True)
    return payload_dir


def _payload_path(doc_id: str | UUID) -> Path:
    return _payload_dir() / f"{doc_id}.bin"


def _get_redis():
    """Return a sync Redis client used for batch update pub/sub."""
    import redis  # type: ignore

    url = os.getenv("REDIS_URL") or os.getenv("DEV_REDIS_URL") or "redis://localhost:6379/0"
    return redis.from_url(url, decode_responses=False)


def store_payload(doc_id: str | UUID, file_bytes: bytes) -> None:
    """Store file bytes on local disk to avoid filling Redis memory."""
    payload_path = _payload_path(doc_id)
    tmp_path = payload_path.with_suffix(".tmp")
    tmp_path.write_bytes(file_bytes)
    tmp_path.replace(payload_path)


def _should_run_inline_ai(
    *,
    tipo_archivo: str,
    estado: str,
    doc_tipo: str,
    raw_ai_json: dict | None = None,
) -> bool:
    """Decide if the inline AI follow-up should run after deterministic import.

    Visual uploads already have a dedicated manual deep-reprocess path.
    Running inline vision on them after the deterministic pass adds latency
    without materially improving the stable import result in the common case.
    """
    if str(tipo_archivo or "").upper() in _INITIAL_VISUAL_FORMATS:
        return False
    run = raw_ai_json.get("run") if isinstance(raw_ai_json, dict) else {}
    run = run if isinstance(run, dict) else {}
    extraction_path = str(run.get("extraction_path") or "").strip().lower()
    if extraction_path in {"fallback", "fallback_error", "partial_timeout_fallback"}:
        return False
    timings = run.get("timings_ms")
    if isinstance(timings, dict) and (
        int(timings.get("ai_primary") or 0) > 0 or int(timings.get("ai_escalation") or 0) > 0
    ):
        return False
    return str(estado or "") == "REVIEW" and str(doc_tipo or "").upper() in ("OTHER", "")


def load_payload(doc_id: str) -> bytes | None:
    """Load file bytes from disk."""
    payload_path = _payload_path(doc_id)
    if payload_path.exists():
        return payload_path.read_bytes()
    return None


def delete_payload(doc_id: str) -> None:
    """Delete temporary payloads from disk."""
    try:
        _payload_path(doc_id).unlink(missing_ok=True)
    except Exception:
        logger.warning("No se pudo eliminar payload local de %s", doc_id, exc_info=True)


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


async def _run_processing(
    doc_id: UUID,
    tenant_id: UUID,
    user_id: str | None,
    file_bytes: bytes,
    filename: str,
    tipo_archivo: str,
    recipe_snapshot_id: str | None = None,
    force: bool = False,
    reprocess_mode: str = "fast",
    reprocess_context: dict | None = None,
) -> None:
    """Run OCR + AI classification + field extraction and update ImpDocumento."""
    from app.config.database import SessionLocal
    from app.modules.importador import crud
    from app.modules.importador.ai_classifier import analyze_document
    from app.modules.importador.ocr_service import extract_text_from_file

    with SessionLocal() as db:
        from sqlalchemy import text as _text

        db.info["tenant_id"] = str(tenant_id)
        db.info["user_id"] = str(user_id) if user_id else None
        # Sin bypass_rls: la política RLS de imp_documento (tenant_isolation, solo
        # app.tenant_id) protege con un rol DB no-superuser. El after_begin reaplica
        # los GUCs desde db.info tras cada commit intermedio.
        db.execute(_text("SELECT 1"))

        from app.models.importador import ImpDocumento

        # Filtra SIEMPRE por tenant_id además del id (defensa en profundidad además de RLS).
        # Un job mal formado con doc_id de otro tenant no debe procesar nada.
        doc = (
            db.query(ImpDocumento)
            .filter(ImpDocumento.id == doc_id, ImpDocumento.tenant_id == tenant_id)
            .first()
        )
        if doc is None:
            logger.error("Documento %s no encontrado en BD para tenant %s", doc_id, tenant_id)
            return

        # Guard de idempotencia: si el doc ya fue procesado, no reprocesar
        if doc and doc.estado in ("REVIEW", "CONFIRMED", "IMPORTED"):
            logger.info(f"[importador] doc {doc_id} ya en estado {doc.estado}, skipping retry")
            return {"status": "skipped", "doc_id": doc_id, "reason": "already_processed"}

        crud.update_documento(db, doc, {"estado": "PROCESSING"})
        for batch_id in crud.touch_batch_items_for_document(db, doc.id, estado="PROCESSING"):
            crud.refresh_batch_status(db, batch_id)
            publish_batch_update(db, batch_id)
        db.commit()
        db.refresh(doc)

        task_started_at = time.perf_counter()
        try:
            await process_import_document(
                db=db,
                doc=doc,
                tenant_id=tenant_id,
                user_id=user_id,
                file_bytes=file_bytes,
                filename=filename,
                tipo_archivo=tipo_archivo,
                force=force,
                extract_text_fn=extract_text_from_file,
                analyze_document_fn=analyze_document,
                recipe_context=RecipeContext(
                    resolution_mode="snapshot" if recipe_snapshot_id else "zero_shot",
                    resolved_snapshot_id=recipe_snapshot_id,
                    explicit_recipe_context=bool(recipe_snapshot_id),
                    reprocess_mode=reprocess_mode,
                    reprocess_context=reprocess_context or {},
                ),
            )
            processing_elapsed_ms = max(
                0, int(round((time.perf_counter() - task_started_at) * 1000))
            )
            commit_started_at = time.perf_counter()
            for batch_id in crud.touch_batch_items_for_document(db, doc.id, estado="REVIEW"):
                crud.refresh_batch_status(db, batch_id)
                publish_batch_update(db, batch_id)
            db.commit()
            db.refresh(doc)
            commit_elapsed_ms = max(0, int(round((time.perf_counter() - commit_started_at) * 1000)))
            total_elapsed_ms = max(0, int(round((time.perf_counter() - task_started_at) * 1000)))
            run_metrics = {}
            if isinstance(getattr(doc, "raw_ai_json", None), dict):
                run_metrics = (
                    (doc.raw_ai_json or {}).get("run", {})
                    if isinstance((doc.raw_ai_json or {}).get("run", {}), dict)
                    else {}
                )
            logger.info(
                "importador.task.completed doc_id=%s metrics=%s",
                doc_id,
                _json_safe(
                    {
                        "tenant_id": str(tenant_id),
                        "batch_processing_ms": processing_elapsed_ms,
                        "batch_commit_ms": commit_elapsed_ms,
                        "batch_total_ms": total_elapsed_ms,
                        "estado": getattr(doc, "estado", None),
                        "run": run_metrics,
                    }
                ),
            )

            # ── IA inline: corre dentro del mismo task cuando el resultado es incierto ──
            # Umbral 0.70: cubre OTHER, correcciones por filename (capeadas a 0.55),
            # tipos promovidos con poca evidencia (0.61-0.68). Docs con confianza alta
            # ya tienen todos los campos relevantes → no necesitan IA.
            _doc_estado = getattr(doc, "estado", "") or ""
            _doc_tipo = str(getattr(doc, "tipo_documento_detectado", "") or "").upper()
            _doc_conf = float(getattr(doc, "confianza_clasificacion", 0.0) or 0.0)

            if _should_run_inline_ai(
                tipo_archivo=tipo_archivo,
                estado=_doc_estado,
                doc_tipo=_doc_tipo,
                raw_ai_json=getattr(doc, "raw_ai_json", None),
            ):
                try:
                    from app.modules.importador.services.ai_analysis_agent import (
                        analyze_document_with_ai as _ai_analyze_inline,
                    )

                    logger.info(
                        "ai_agent.inline_start doc_id=%s tipo=%s conf=%.3f",
                        doc_id,
                        _doc_tipo,
                        _doc_conf,
                    )
                    await _ai_analyze_inline(
                        doc_id=doc_id,
                        db=db,
                        apply_result=True,
                    )
                    db.refresh(doc)
                    logger.info(
                        "ai_agent.inline_done doc_id=%s tipo_final=%s conf_final=%.3f",
                        doc_id,
                        getattr(doc, "tipo_documento_detectado", ""),
                        float(getattr(doc, "confianza_clasificacion", 0.0) or 0.0),
                    )
                except Exception as _ai_exc:
                    # No propagar: si falla la IA el doc queda con el resultado determinístico
                    logger.warning("ai_agent.inline_failed doc_id=%s: %s", doc_id, _ai_exc)
            elif _doc_estado == "REVIEW" and _doc_tipo in ("OTHER", ""):
                logger.info(
                    "ai_agent.inline_skipped doc_id=%s reason=visual_doc tipo=%s",
                    doc_id,
                    tipo_archivo,
                )

        except Exception as exc:
            logger.error("Error procesando documento %s: %s", doc_id, exc, exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                from app.models.importador import ImpDocumento as _ImpDoc

                fresh_doc = db.get(_ImpDoc, doc_id)
                if fresh_doc:
                    crud.update_documento(
                        db, fresh_doc, {"estado": "FAILED", "error_detalle": str(exc)}
                    )
                    crud.add_log(db, fresh_doc.id, "EXTRACT", user_id, {"error": str(exc)})
                    for batch_id in crud.touch_batch_items_for_document(
                        db,
                        fresh_doc.id,
                        estado="FAILED",
                        error_detalle=str(exc),
                    ):
                        crud.refresh_batch_status(db, batch_id)
                        publish_batch_update(db, batch_id)
                    db.commit()
            except Exception as inner:
                logger.error("No se pudo marcar FAILED doc %s: %s", doc_id, inner, exc_info=True)


def _make_task():
    """Register the Celery task lazily to avoid startup failures."""
    try:
        from celery_app import get_celery_app  # type: ignore

        celery_app = get_celery_app()
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
        reprocess_mode: str = "fast",
        reprocess_context: dict | None = None,
    ) -> dict:
        logger.info("Iniciando procesamiento async de documento %s (%s)", doc_id, filename)

        file_bytes = load_payload(doc_id)
        if not file_bytes:
            storage_path = _payload_path(doc_id)
            technical_msg = f"Payload no encontrado para doc {doc_id}; puede haber expirado"
            user_msg = (
                "No se pudo recuperar el archivo para procesarlo. "
                "Vuelve a subirlo o inténtalo de nuevo."
            )
            logger.error("%s (storage=%s)", technical_msg, storage_path)
            try:
                from app.config.database import SessionLocal
                from app.models.importador import ImpDocumento
                from app.modules.importador import crud

                with SessionLocal() as db:
                    from sqlalchemy import text as _text

                    db.info["tenant_id"] = tenant_id
                    db.execute(_text("SELECT 1"))
                    # Sin bypass: RLS por tenant + filtro explícito (defensa en profundidad).
                    doc = (
                        db.query(ImpDocumento)
                        .filter(
                            ImpDocumento.id == UUID(doc_id),
                            ImpDocumento.tenant_id == UUID(str(tenant_id)),
                        )
                        .first()
                    )
                    if doc:
                        # Si el documento ya tiene datos extraídos de un ciclo anterior, NO
                        # marcarlo como FAILED: la extracción fue exitosa. Solo registrar que
                        # el archivo original ya no está disponible para reprocesar.
                        tiene_datos = bool(
                            doc.datos_extraidos
                            and isinstance(doc.datos_extraidos, dict)
                            and doc.datos_extraidos
                        )
                        if tiene_datos:
                            doc_update: dict = {"reprocess_status": "unavailable"}
                            batch_estado = doc.estado  # preservar estado actual (REVIEW, etc.)
                            logger.warning(
                                "Payload no encontrado para doc %s pero tiene datos extraídos; "
                                "marcando reprocess_status=unavailable sin cambiar estado=%s",
                                doc_id,
                                doc.estado,
                            )
                        else:
                            doc_update = {
                                "estado": "FAILED",
                                "error_detalle": user_msg,
                                "extraction_status": "failed",
                                "reprocess_status": "unavailable",
                            }
                            batch_estado = "FAILED"

                        crud.update_documento(db, doc, doc_update)
                        for batch_id in crud.touch_batch_items_for_document(
                            db,
                            doc.id,
                            estado=batch_estado,
                            error_detalle=user_msg if not tiene_datos else None,
                        ):
                            crud.refresh_batch_status(db, batch_id)
                            publish_batch_update(db, batch_id)
                        db.commit()
            except Exception as exc:
                logger.error("No se pudo actualizar estado doc %s: %s", doc_id, exc)
            return {"ok": False, "error": user_msg}

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
                    reprocess_mode=reprocess_mode,
                    reprocess_context=reprocess_context,
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


# ── Tarea Celery para análisis IA (solo lectura) ───────────────────────────────


def _make_ai_analysis_task():
    """Registra la tarea de análisis IA. Read-only: no modifica BD."""
    try:
        from celery_app import get_celery_app  # type: ignore

        celery_app = get_celery_app()
    except Exception:
        return None

    @celery_app.task(
        name="importador.analyze_document_ai",
        bind=True,
        queue="importador_deep",
        max_retries=1,
        default_retry_delay=15,
        time_limit=180,
        soft_time_limit=150,
        acks_late=True,
    )
    def analyze_document_ai(
        self,
        doc_id: str,
        tenant_id: str,
        bypass_cache: bool = False,
    ) -> dict:
        """Tarea Celery: analiza un documento con IA sin modificar la BD.

        Resultado completo accesible via result_backend de Celery.
        Los logs de comparación quedan en importador.ai_agent.
        """
        from app.config.database import SessionLocal
        from app.modules.importador.services.ai_analysis_agent import analyze_document_with_ai

        logger.info("ai_agent.task.start doc_id=%s tenant=%s", doc_id, tenant_id)
        try:
            with SessionLocal() as db:
                from sqlalchemy import text as _text

                db.info["tenant_id"] = tenant_id
                # Sin bypass: RLS por tenant. analyze_document_with_ai además valida tenant.
                db.execute(_text("SELECT 1"))

                result = asyncio.run(
                    analyze_document_with_ai(
                        doc_id=UUID(doc_id),
                        db=db,
                        tenant_id=UUID(str(tenant_id)),
                        bypass_cache=bypass_cache,
                    )
                )

            logger.info(
                "ai_agent.task.done doc_id=%s match=%s ai_type=%s",
                doc_id,
                result.get("comparison", {}).get("type_match"),
                result.get("comparison", {}).get("ai_type"),
            )
            return {"ok": True, "doc_id": doc_id, "result": result}

        except Exception as exc:
            logger.error("ai_agent.task.error doc_id=%s: %s", doc_id, exc, exc_info=True)
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                return {"ok": False, "doc_id": doc_id, "error": str(exc)}

    return analyze_document_ai


analyze_document_ai_task = _make_ai_analysis_task()
