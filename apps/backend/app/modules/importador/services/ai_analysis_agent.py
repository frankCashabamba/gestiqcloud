"""Agente de análisis IA para el importador.

El agente se ejecuta después del procesamiento determinístico y aplica
los resultados del LLM cuando mejoran lo que el sistema nativo encontró.

Reglas de aplicación (conservadoras):
  1. Det=OTHER + AI tiene tipo real con confianza ≥ 0.50 → sobrescribe tipo + campos + confianza
  2. Det tiene tipo + AI encontró campos nuevos → mergea solo los campos nuevos
  3. Siempre guarda resultado IA en raw_ai_json["ai_enrichment"] para auditoría

Lo que NO hace:
  - Cambiar el tipo si el determinístico ya clasificó (salvo que confianza AI sea muy superior)
  - Eliminar campos que el determinístico encontró
  - Modificar el estado del documento (siempre queda en REVIEW)
"""

from __future__ import annotations

import datetime
import inspect
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger("importador.ai_agent")


async def _call_ai_analyze(_ai_analyze, content: str, filename: str, format_hint: str, **kwargs):
    try:
        signature = inspect.signature(_ai_analyze)
    except (TypeError, ValueError):
        return await _ai_analyze(
            content=content,
            filename=filename,
            format_hint=format_hint,
            **kwargs,
        )
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        filtered_kwargs = kwargs
    else:
        filtered_kwargs = {
            key: value for key, value in kwargs.items() if key in signature.parameters
        }
    return await _ai_analyze(
        content=content,
        filename=filename,
        format_hint=format_hint,
        **filtered_kwargs,
    )


# Confianza mínima para que la IA sobrescriba un tipo OTHER
_MIN_AI_CONFIDENCE_FOR_TYPE_OVERRIDE = 0.50
# Delta mínimo de confianza para que la IA cambie un tipo ya clasificado
_MIN_CONFIDENCE_DELTA_FOR_TYPE_CHANGE = 0.20


# ── Carga de imagen desde caché OCR ───────────────────────────────────────────


def _load_vision_image_from_cache(hash_sha256: str | None) -> bytes | None:
    """Devuelve los bytes JPEG del caché OCR sin reejecutar Tesseract.

    El caché OCR guarda 'vision_image_b64' junto al texto extraído.
    Lo recuperamos directamente usando el hash SHA-256 del fichero
    (almacenado en ImpDocumento.hash_sha256) sin necesitar el fichero original.

    Devuelve None si el caché no existe, expiró o no tiene imagen.
    """
    if not hash_sha256:
        return None
    import base64
    import json

    from app.config.settings import settings
    from app.modules.importador.ocr_service import OCR_EXTRACTION_CACHE_VERSION

    cache_path = settings.uploads_path / "_importador_ocr_cache" / f"{hash_sha256}.json"
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("version") != OCR_EXTRACTION_CACHE_VERSION:
        return None  # caché obsoleto — se regenerará en la próxima importación
    b64 = payload.get("vision_image_b64")
    if not b64:
        return None
    try:
        return base64.b64decode(b64.encode("ascii"))
    except Exception:
        return None


# ── Resultado estructurado ─────────────────────────────────────────────────────


def _build_comparison(
    det: dict[str, Any],
    ai: dict[str, Any],
) -> dict[str, Any]:
    """Compara resultado determinístico vs IA y devuelve un resumen de diferencias."""
    det_type = str(det.get("doc_type") or "").upper()
    ai_type = str(ai.get("doc_type") or "").upper()

    det_fields: dict = det.get("fields") or {}
    ai_fields: dict = ai.get("fields") or {}

    det_keys = {k for k, v in det_fields.items() if v not in (None, "", [], {})}
    ai_keys = {k for k, v in ai_fields.items() if v not in (None, "", [], {})}

    new_fields = sorted(ai_keys - det_keys)
    lost_fields = sorted(det_keys - ai_keys)

    improved_fields = []
    for key in det_keys & ai_keys:
        det_val = det_fields.get(key)
        ai_val = ai_fields.get(key)
        if ai_val and (not det_val or str(ai_val) != str(det_val)):
            improved_fields.append(key)

    return {
        "type_match": det_type == ai_type,
        "det_type": det_type,
        "ai_type": ai_type,
        "det_confidence": round(float(det.get("confidence") or 0.0), 3),
        "ai_confidence": round(float(ai.get("confidence") or 0.0), 3),
        "new_fields": new_fields,
        "lost_fields": lost_fields,
        "improved_fields": improved_fields,
        "det_field_count": len(det_keys),
        "ai_field_count": len(ai_keys),
    }


# ── Persistencia de resultados IA ──────────────────────────────────────────────


def _apply_ai_result_to_doc(
    *,
    doc: Any,
    deterministic: dict[str, Any],
    ai_summary: dict[str, Any],
    comparison: dict[str, Any],
    db: Any,
) -> dict[str, Any]:
    """Aplica el resultado IA al documento en BD cuando aporta valor real.

    Reglas (conservadoras):
      1. Det=OTHER + AI tiene tipo real con confianza ≥ 0.50 → sobrescribe tipo+confianza+campos
      2. Cualquier caso + AI encontró campos nuevos → mergea solo esos campos
      3. Siempre guarda ai_enrichment en raw_ai_json para auditoría

    Returns:
        Dict con las claves aplicadas (vacío si no hubo cambios).
    """
    from app.modules.importador import crud

    det_type = comparison["det_type"]
    ai_type = comparison["ai_type"]
    ai_confidence = comparison["ai_confidence"]
    det_confidence = comparison["det_confidence"]
    new_fields = comparison["new_fields"]

    ai_fields: dict = ai_summary.get("fields") or {}
    current_fields: dict = dict(doc.datos_extraidos or {})

    applied: dict[str, Any] = {}

    # ── Caso 1: determinístico no clasificó (OTHER), IA tiene tipo real ─────────
    override_type = (
        det_type == "OTHER"
        and ai_type not in ("OTHER", "")
        and ai_confidence >= _MIN_AI_CONFIDENCE_FOR_TYPE_OVERRIDE
    )
    if override_type:
        # Mergear campos: base determinística + campos nuevos de IA
        merged_fields = {**current_fields}
        for k, v in ai_fields.items():
            if v not in (None, "", [], {}):
                merged_fields[k] = v

        applied["tipo_documento_detectado"] = ai_type
        applied["confianza_clasificacion"] = ai_confidence
        applied["datos_extraidos"] = merged_fields
        logger.info(
            "ai_agent.apply.type_override doc_id=%s OTHER→%s confidence=%.3f fields_added=%s",
            doc.id,
            ai_type,
            ai_confidence,
            sorted(set(merged_fields) - set(current_fields)),
        )

    # ── Caso 2: tipos coinciden o det ya tiene tipo, pero IA encontró más campos ─
    elif new_fields:
        merged_fields = {**current_fields}
        for k in new_fields:
            v = ai_fields.get(k)
            if v not in (None, "", [], {}):
                merged_fields[k] = v
                applied[f"field_added_{k}"] = v  # solo para el log de retorno

        if len(merged_fields) > len(current_fields):
            applied["datos_extraidos"] = merged_fields
            logger.info(
                "ai_agent.apply.new_fields doc_id=%s type=%s new_fields=%s",
                doc.id,
                det_type,
                new_fields,
            )

    # ── Siempre: guardar resultado IA en raw_ai_json para auditoría ─────────────
    existing_raw = dict(doc.raw_ai_json or {}) if isinstance(doc.raw_ai_json, dict) else {}
    existing_raw["ai_enrichment"] = {
        "analyzed_at": datetime.datetime.utcnow().isoformat() + "Z",
        "ai_type": ai_type,
        "ai_confidence": ai_confidence,
        "det_type": det_type,
        "det_confidence": det_confidence,
        "type_overridden": override_type,
        "new_fields_applied": (
            new_fields if "datos_extraidos" in applied and not override_type else []
        ),
        "model_used": ai_summary.get("model_used", ""),
        "elapsed_ms": ai_summary.get("elapsed_ms", 0),
    }
    applied["raw_ai_json"] = existing_raw

    if applied:
        update_payload = {k: v for k, v in applied.items() if not k.startswith("field_added_")}
        crud.update_documento(db, doc, update_payload)
        db.commit()
        logger.info(
            "ai_agent.applied doc_id=%s keys=%s",
            doc.id,
            [k for k in update_payload if k != "raw_ai_json"],
        )

    return applied


# ── Análisis de un documento ───────────────────────────────────────────────────


async def analyze_document_with_ai(
    *,
    doc_id: UUID,
    db: Any,
    bypass_cache: bool = False,
    apply_result: bool = True,
) -> dict[str, Any]:
    """Analiza un documento ya procesado con IA y aplica mejoras en BD.

    Args:
        doc_id:        ID del documento en imp_documento.
        db:            Sesión SQLAlchemy activa.
        bypass_cache:  Si True, fuerza llamada al LLM sin caché.
        apply_result:  Si True (default), persiste mejoras en BD cuando las hay.

    Returns:
        Dict con claves:
          doc_id, filename, estado, analyzed_at,
          deterministic (tipo, confianza, campos),
          ai (tipo, confianza, campos, reasoning, model_used, elapsed_ms),
          comparison (type_match, new_fields, …),
          applied (qué se escribió en BD, vacío si nada cambió),
          error (solo si falla).
    """
    from app.models.importador import ImpDocumento
    from app.modules.importador.ai_classifier import analyze_document as _ai_analyze
    from app.modules.importador.field_alias_loader import get_canonical_fields
    from app.modules.importador.runtime_config import load_doc_type_patterns, load_prompt_config

    doc: ImpDocumento | None = db.get(ImpDocumento, doc_id)
    if doc is None:
        return {"doc_id": str(doc_id), "error": "documento no encontrado"}

    filename = str(doc.nombre_archivo or "")
    tipo_archivo = str(doc.tipo_archivo or "PDF").upper()
    ocr_text = str(doc.texto_ocr or "").strip()

    if not ocr_text:
        logger.warning("ai_agent doc_id=%s sin texto OCR disponible", doc_id)
        return {
            "doc_id": str(doc_id),
            "filename": filename,
            "error": "sin texto OCR almacenado; reimportar primero",
        }

    # Intentar cargar imagen del caché OCR para enviar al LLM en modo visión.
    # Reutiliza lo que Tesseract ya procesó — no vuelve a ejecutar OCR.
    vision_image_bytes = _load_vision_image_from_cache(getattr(doc, "hash_sha256", None))
    _image_source = "ocr_cache" if vision_image_bytes else "none"
    logger.debug(
        "ai_agent doc_id=%s vision_image=%s hash=%s",
        doc_id,
        _image_source,
        getattr(doc, "hash_sha256", None),
    )

    # ── Resultado determinístico actual ────────────────────────────────────────
    deterministic = {
        "doc_type": str(doc.tipo_documento_detectado or "OTHER").upper(),
        "confidence": float(doc.confianza_clasificacion or 0.0),
        "fields": dict(doc.datos_extraidos or {}),
    }

    # ── Cargar configuración de runtime ───────────────────────────────────────
    try:
        fallback_patterns = load_doc_type_patterns(db)
        canonical_fields = get_canonical_fields(db)
        prompt_config = load_prompt_config(db)
    except Exception as exc:
        logger.warning("ai_agent config_load_error doc_id=%s: %s", doc_id, exc)
        fallback_patterns = {}
        canonical_fields = {}
        prompt_config = {}

    # ── Llamada al LLM ─────────────────────────────────────────────────────────
    logger.info(
        "ai_agent.start doc_id=%s filename=%s format=%s chars=%s det_type=%s vision=%s",
        doc_id,
        filename,
        tipo_archivo,
        len(ocr_text),
        deterministic["doc_type"],
        _image_source,
    )

    ai_result: dict[str, Any] = {}
    elapsed_ms = 0
    error: str | None = None

    _use_vision = vision_image_bytes is not None
    _is_image_format = tipo_archivo.upper() in (
        "JPG",
        "JPEG",
        "PNG",
        "HEIC",
        "WEBP",
        "PDF_OCR",
        "IMAGE_OCR",
    )

    t0 = time.perf_counter()
    try:
        ai_result = await _call_ai_analyze(
            _ai_analyze,
            content=ocr_text,
            filename=filename,
            format_hint=tipo_archivo,
            has_structured_rows=False,
            pre_extracted_fields=deterministic["fields"] or None,
            image_bytes=vision_image_bytes if _use_vision else None,
            fallback_patterns=fallback_patterns,
            canonical_fields=canonical_fields,
            prompt_config=prompt_config,
            db=db,
            reprocess_mode="fast",
            bypass_cache=bypass_cache,
            force_vision=_use_vision and _is_image_format,
            vision_first=_use_vision,
        )
    except Exception as exc:
        error = str(exc)
        logger.error("ai_agent.llm_error doc_id=%s: %s", doc_id, exc, exc_info=True)
    finally:
        elapsed_ms = int(round((time.perf_counter() - t0) * 1000))

    if error:
        return {
            "doc_id": str(doc_id),
            "filename": filename,
            "error": error,
            "elapsed_ms": elapsed_ms,
        }

    # ── Comparación ────────────────────────────────────────────────────────────
    ai_summary = {
        "doc_type": str(ai_result.get("doc_type") or "OTHER").upper(),
        "confidence": round(float(ai_result.get("confidence") or 0.0), 3),
        "fields": dict(ai_result.get("fields") or {}),
        "reasoning": str(ai_result.get("reasoning") or ""),
        "model_used": str(ai_result.get("model_used") or ""),
        "elapsed_ms": elapsed_ms,
    }

    comparison = _build_comparison(deterministic, ai_summary)

    logger.info(
        "ai_agent.done doc_id=%s det=%s ai=%s match=%s new_fields=%s improved=%s elapsed_ms=%s",
        doc_id,
        comparison["det_type"],
        comparison["ai_type"],
        comparison["type_match"],
        comparison["new_fields"],
        comparison["improved_fields"],
        elapsed_ms,
    )

    # ── Aplicar resultados en BD ───────────────────────────────────────────────
    applied: dict[str, Any] = {}
    if apply_result:
        try:
            # Refrescar el doc para evitar conflictos de versión con el commit anterior
            db.refresh(doc)
            applied = _apply_ai_result_to_doc(
                doc=doc,
                deterministic=deterministic,
                ai_summary=ai_summary,
                comparison=comparison,
                db=db,
            )
        except Exception as exc:
            logger.error("ai_agent.apply_error doc_id=%s: %s", doc_id, exc, exc_info=True)

    return {
        "doc_id": str(doc_id),
        "filename": filename,
        "estado": str(getattr(doc, "estado", "") or ""),
        "analyzed_at": datetime.datetime.utcnow().isoformat() + "Z",
        "deterministic": deterministic,
        "ai": ai_summary,
        "comparison": comparison,
        "applied": {k: v for k, v in applied.items() if not k.startswith("field_added_")},
    }


# ── Análisis en lote ───────────────────────────────────────────────────────────


async def analyze_batch_with_ai(
    *,
    tenant_id: UUID,
    db: Any,
    estado: str = "REVIEW",
    doc_type_filter: str | None = None,
    limit: int = 10,
    bypass_cache: bool = False,
    apply_result: bool = True,
) -> dict[str, Any]:
    """Analiza un lote de documentos en REVIEW con IA y aplica mejoras en BD.

    Args:
        tenant_id:        Tenant a analizar.
        db:               Sesión SQLAlchemy.
        estado:           Filtrar por este estado (default: REVIEW).
        doc_type_filter:  Si se pasa, solo analiza ese tipo (ej. "INVOICE").
        limit:            Máximo de documentos por lote.
        bypass_cache:     Forzar LLM sin caché.
        apply_result:     Si True, persiste mejoras en BD.
    """
    from sqlalchemy import select

    from app.models.importador import ImpDocumento

    stmt = select(ImpDocumento.id).where(
        ImpDocumento.tenant_id == tenant_id,
        ImpDocumento.estado == estado,
        ImpDocumento.texto_ocr.isnot(None),
        ImpDocumento.texto_ocr != "",
    )
    if doc_type_filter:
        stmt = stmt.where(ImpDocumento.tipo_documento_detectado == doc_type_filter.upper())

    stmt = stmt.order_by(ImpDocumento.created_at.desc()).limit(limit)
    rows = db.execute(stmt).all()
    doc_ids = [row[0] for row in rows]

    logger.info(
        "ai_agent.batch_start tenant=%s estado=%s doc_type=%s limit=%s found=%s",
        tenant_id,
        estado,
        doc_type_filter or "*",
        limit,
        len(doc_ids),
    )

    results: list[dict[str, Any]] = []
    errors = 0

    for doc_id in doc_ids:
        result = await analyze_document_with_ai(
            doc_id=doc_id,
            db=db,
            bypass_cache=bypass_cache,
            apply_result=apply_result,
        )
        results.append(result)
        if "error" in result:
            errors += 1

    # ── Resumen del lote ───────────────────────────────────────────────────────
    successful = [r for r in results if "error" not in r]
    type_matches = sum(1 for r in successful if r.get("comparison", {}).get("type_match"))
    new_fields_total = sum(len(r.get("comparison", {}).get("new_fields", [])) for r in successful)
    type_changes = [
        {
            "doc_id": r["doc_id"],
            "filename": r.get("filename", ""),
            "det_type": r["comparison"]["det_type"],
            "ai_type": r["comparison"]["ai_type"],
        }
        for r in successful
        if not r.get("comparison", {}).get("type_match")
    ]
    applied_count = sum(1 for r in successful if r.get("applied"))

    n = len(successful)
    summary = {
        "type_match_rate": round(type_matches / n, 3) if n else 0.0,
        "type_match_count": type_matches,
        "type_mismatch_count": n - type_matches,
        "type_changes": type_changes,
        "new_fields_total": new_fields_total,
        "new_fields_avg": round(new_fields_total / n, 2) if n else 0.0,
        "applied_count": applied_count,
    }

    logger.info(
        "ai_agent.batch_done tenant=%s analyzed=%s errors=%s match_rate=%.2f "
        "type_changes=%s applied=%s",
        tenant_id,
        n,
        errors,
        summary["type_match_rate"],
        len(type_changes),
        applied_count,
    )

    return {
        "total": len(doc_ids),
        "analyzed": n,
        "errors": errors,
        "results": results,
        "summary": summary,
    }
