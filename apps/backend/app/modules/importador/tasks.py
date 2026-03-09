"""Celery tasks para el Importador Contable Universal.

Flujo async:
  1. POST /importador/run-async → guarda bytes en Redis, crea ImpDocumento(PENDING), encola task
  2. importador.process_document (esta task) → procesa, actualiza ImpDocumento(REVIEW|FAILED)
  3. Frontend polling GET /importador/documents/{id} hasta estado != PENDING|PROCESSING

No toca la lógica existente de router.py — reutiliza las mismas funciones de OCR y AI.
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

logger = logging.getLogger("importador.tasks")

REDIS_KEY_PREFIX = "imp:payload:"
REDIS_TTL = 3600  # 1 hora — suficiente para cualquier procesamiento


# ---------------------------------------------------------------------------
# Helpers Redis
# ---------------------------------------------------------------------------

def _get_redis():
    """Retorna cliente Redis síncrono (redis-py)."""
    import redis  # type: ignore

    url = os.getenv("REDIS_URL") or os.getenv("DEV_REDIS_URL") or "redis://localhost:6379/0"
    return redis.from_url(url, decode_responses=False)


def store_payload(doc_id: str | UUID, file_bytes: bytes) -> None:
    """Guarda los bytes del archivo en Redis con TTL."""
    r = _get_redis()
    r.set(f"{REDIS_KEY_PREFIX}{doc_id}", file_bytes, ex=REDIS_TTL)


def load_payload(doc_id: str) -> bytes | None:
    """Recupera los bytes del archivo desde Redis."""
    r = _get_redis()
    return r.get(f"{REDIS_KEY_PREFIX}{doc_id}")


def delete_payload(doc_id: str) -> None:
    """Elimina los bytes del archivo de Redis tras procesamiento."""
    r = _get_redis()
    r.delete(f"{REDIS_KEY_PREFIX}{doc_id}")


def publish_status(doc_id: str, estado: str) -> None:
    """Publica el estado final en Redis pub/sub.

    El endpoint SSE /documents/{id}/stream suscribe a este canal y pushea
    el evento al cliente, eliminando el polling HTTP masivo.
    Canal: imp:status:{doc_id}
    """
    import json

    try:
        r = _get_redis()
        r.publish(f"imp:status:{doc_id}", json.dumps({"estado": estado}))
    except Exception as exc:  # Redis no disponible → no es crítico
        logger.warning("pub/sub no disponible para doc %s: %s", doc_id, exc)


# ---------------------------------------------------------------------------
# Lógica de procesamiento (async) — mismas funciones que router.py
# ---------------------------------------------------------------------------

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
    """Ejecuta OCR + clasificación AI + extracción de campos y actualiza ImpDocumento."""
    import datetime
    import hashlib

    from app.config.database import SessionLocal
    from app.modules.importador import crud
    from app.modules.importador.ai_classifier import CONFIDENCE_THRESHOLD, analyze_document
    from app.modules.importador.auto_recipe import resolve_auto_recipe
    from app.modules.importador.document_fields import (
        detect_document_currency,
        detect_document_date,
        detect_document_total,
        get_data_value,
    )
    from app.modules.importador.ocr_service import extract_text_from_file

    def _json_safe(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _json_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_json_safe(v) for v in obj]
        return obj

    with SessionLocal() as db:
        doc = db.get(type(crud.get_documento(db, doc_id)), doc_id)
        if doc is None:
            # Buscar con query directa
            from app.models.importador import ImpDocumento
            doc = db.query(ImpDocumento).filter(ImpDocumento.id == doc_id).first()
        if doc is None:
            logger.error("Documento %s no encontrado en BD", doc_id)
            return

        # Marcar como procesando
        crud.update_documento(db, doc, {"estado": "PROCESSING"})
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

            # Resolver receta automática
            resolved_snapshot_id = None
            resolution_mode = "zero_shot"
            if sheet_profiles:
                _, resolved_snapshot_id, resolution_mode, _, _ = resolve_auto_recipe(
                    db, str(tenant_id), sheet_profiles, user_id
                )
            if recipe_snapshot_id:
                resolved_snapshot_id = recipe_snapshot_id

            # Contenido para el LLM
            if has_structured:
                sample_lines = [f"Columnas: {headers_display}"]
                for row in (structured[:5] if isinstance(structured, list) else []):
                    if isinstance(row, dict):
                        sample_lines.append(
                            str({k: v for k, v in list(row.items())[:8] if not k.startswith("_")})
                        )
                llm_content = "\n".join(sample_lines)
            else:
                llm_content = text[:6000] if text else ""

            analysis = await analyze_document(
                llm_content,
                filename,
                extraction.get("format", tipo_archivo),
                has_structured_rows=has_structured,
                recipe_config={},
            )

            tipo_doc = analysis.get("doc_type", "OTHER")
            confianza = float(analysis.get("confidence", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD

            crud.add_log(db, doc.id, "CLASSIFY", user_id, {
                "tipo_documento": tipo_doc,
                "confianza": confianza,
                "razonamiento": analysis.get("reasoning", ""),
                "model_used": analysis.get("model_used"),
            })

            # Datos extraídos
            if has_structured:
                sheet_used_str = extraction.get("sheet_used")
                sheet_metadata_raw = extraction.get("sheet_metadata") or {}
                filas_por_hoja_raw: dict[str, list] = {}
                for _row in structured or []:
                    if isinstance(_row, dict):
                        _sname = str(_row.get("_sheet") or sheet_used_str or "")
                        if _sname:
                            filas_por_hoja_raw.setdefault(_sname, []).append(_row)
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

            crud.add_log(db, doc.id, "EXTRACT", user_id, {
                "campos_extraidos": (
                    list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
                )
            })

            datos_extraidos = _json_safe(datos_extraidos) if isinstance(datos_extraidos, (dict, list)) else datos_extraidos
            sheet_profiles = _json_safe(sheet_profiles) if isinstance(sheet_profiles, (dict, list)) else sheet_profiles

            crud.update_documento(db, doc, {
                "texto_ocr": text[:50000],
                "tipo_documento_detectado": tipo_doc,
                "confianza_clasificacion": confianza,
                "requiere_revision": requiere_revision,
                "datos_extraidos": datos_extraidos,
                "estado": "REVIEW",
                "proveedor_detectado": (
                    get_data_value(datos_extraidos, "vendor", "proveedor", "vendor_name", "supplier", "emisor")
                    if isinstance(datos_extraidos, dict) else None
                ),
                "ruc_detectado": (
                    get_data_value(datos_extraidos, "vendor_tax_id", "ruc", "tax_id", "supplier_tax_id", "ruc_proveedor")
                    if isinstance(datos_extraidos, dict) else None
                ),
                "monto_total": (
                    detect_document_total(datos_extraidos) if isinstance(datos_extraidos, dict) else None
                ),
                "moneda": (
                    detect_document_currency(datos_extraidos) if isinstance(datos_extraidos, dict) else None
                ),
                "fecha_documento": (
                    detect_document_date(datos_extraidos) if isinstance(datos_extraidos, dict) else None
                ),
                "fingerprint_json": sheet_profiles,
                "sheet_profiles_json": sheet_profiles,
                "llm_model": analysis.get("model_used"),
                "recipe_snapshot_id": resolved_snapshot_id,
            })
            db.commit()
            publish_status(str(doc_id), "REVIEW")
            logger.info("Documento %s procesado correctamente → REVIEW", doc_id)

        except Exception as exc:
            logger.error("Error procesando documento %s: %s", doc_id, exc, exc_info=True)
            crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": str(exc)})
            crud.add_log(db, doc.id, "EXTRACT", user_id, {"error": str(exc)})
            db.commit()
            publish_status(str(doc_id), "FAILED")


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

def _make_task():
    """Importa celery_app y registra la task. Importación diferida para evitar
    errores de arranque cuando Redis no está disponible."""
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
        """Procesa un documento importado de forma asíncrona."""
        logger.info("Iniciando procesamiento async de documento %s (%s)", doc_id, filename)

        file_bytes = load_payload(doc_id)
        if not file_bytes:
            msg = f"Payload no encontrado en Redis para doc {doc_id} — puede haber expirado"
            logger.error(msg)
            # Marcar como FAILED en BD
            try:
                from app.config.database import SessionLocal
                from app.models.importador import ImpDocumento
                with SessionLocal() as db:
                    doc = db.query(ImpDocumento).filter(ImpDocumento.id == UUID(doc_id)).first()
                    if doc:
                        from app.modules.importador import crud
                        crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": msg})
                        db.commit()
                        publish_status(doc_id, "FAILED")
            except Exception as e:
                logger.error("No se pudo marcar FAILED doc %s: %s", doc_id, e)
            return {"ok": False, "error": msg}

        try:
            asyncio.run(_run_processing(
                doc_id=UUID(doc_id),
                tenant_id=UUID(tenant_id),
                user_id=user_id,
                file_bytes=file_bytes,
                filename=filename,
                tipo_archivo=tipo_archivo,
                recipe_snapshot_id=recipe_snapshot_id,
                force=force,
            ))
        except Exception as exc:
            logger.error("Task falló para doc %s: %s", doc_id, exc, exc_info=True)
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                return {"ok": False, "error": str(exc)}
        finally:
            # Limpiar payload de Redis en cualquier caso
            delete_payload(doc_id)

        return {"ok": True, "doc_id": doc_id}

    return process_document


# Registrar la task al importar el módulo (si Celery está disponible)
process_document_task = _make_task()
