from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("importador.runtime_config")

_CACHE_TTL = 300.0
_cache: dict[str, tuple[float, dict]] = {}

_RUNTIME_SEED_PATH = Path(__file__).with_name("runtime_seed.json")

_DEFAULT_FILE_SUPPORT = {
    "accepted_extensions": [
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".heic",
        ".heif",
        ".tiff",
        ".bmp",
        ".gif",
        ".xlsx",
        ".xls",
        ".csv",
        ".xml",
        ".txt",
        ".zip",
    ],
    "image_extensions": [".png", ".jpg", ".jpeg", ".heic", ".heif", ".tiff", ".bmp", ".gif"],
    "type_map": {
        ".pdf": "PDF",
        ".jpg": "JPG",
        ".jpeg": "JPG",
        ".png": "PNG",
        ".heic": "IMG",
        ".heif": "IMG",
        ".tiff": "IMG",
        ".bmp": "IMG",
        ".gif": "IMG",
        ".xlsx": "XLSX",
        ".xls": "XLS",
        ".csv": "CSV",
        ".xml": "XML",
        ".txt": "TXT",
        ".zip": "ZIP",
    },
}

_DEFAULT_CLASSIFICATION_CONFIG: dict[str, float] = {
    "confidence_threshold": 0.85,
}

_DEFAULT_LEARNING_CONFIG: dict[str, float] = {
    "event_weight_save": 4.0,
    "event_weight_confirm": 3.0,
    "event_weight_edit": 1.35,
    "event_weight_default": 1.0,
    "quality_bonus_required_fields_ok": 0.75,
    "quality_bonus_no_review_needed": 0.45,
    "quality_bonus_has_destination": 0.35,
    "filename_pattern_base_confidence": 0.65,
}


def _cache_get(key: str) -> dict | None:
    entry = _cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if (time.monotonic() - ts) > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: dict) -> dict:
    _cache[key] = (time.monotonic(), value)
    return value


def _load_module_rows(db: Any, module: str) -> list[Any]:
    """Load all ImpConfig rows for a given module (sin prefijo 'importador.')."""
    from app.models.importador import ImpConfig

    return db.query(ImpConfig).filter(ImpConfig.module == module).all()


def _load_runtime_seed() -> dict[str, Any]:
    try:
        payload = json.loads(_RUNTIME_SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("No se pudo cargar runtime seed del importador: %s", exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def _seed_module_payload(module: str) -> dict[str, Any]:
    payload = _load_runtime_seed().get(module)
    return payload if isinstance(payload, dict) else {}


def _ensure_module_seeded(db: Any, module: str) -> list[Any]:
    rows = _load_module_rows(db, module)
    if rows:
        return rows

    payload = _seed_module_payload(module)
    if not payload:
        return rows

    try:
        from app.models.importador import ImpConfig

        for key, value in payload.items():
            db.add(
                ImpConfig(
                    module=module,
                    key=str(key),
                    value_text=(str(value).strip() if isinstance(value, str) else None),
                    value_list=(list(value) if isinstance(value, list) else None),
                    label=f"Seeded runtime config for {module}.{key}",
                )
            )
        db.commit()
        return _load_module_rows(db, module)
    except Exception as exc:
        logger.warning("No se pudo sembrar imp_config para %s: %s", module, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return rows


def load_doc_type_patterns(db: Any) -> dict[str, list[str]]:
    cached = _cache_get("doc_type_patterns")
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        rows = _ensure_module_seeded(db, "doc_type_patterns")
        patterns: dict[str, list[str]] = {}
        for row in rows:
            if not isinstance(row.value_list, list):
                continue
            values = [str(v).strip().lower() for v in row.value_list if str(v).strip()]
            if values:
                patterns[str(row.key).strip().upper()] = values
        if patterns:
            return _cache_set("doc_type_patterns", patterns)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar doc_type_patterns desde imp_config: %s", exc)

    seed = _seed_module_payload("doc_type_patterns")
    return {
        str(key).strip().upper(): list(value)
        for key, value in seed.items()
        if isinstance(value, list)
    }


def load_file_support_config(db: Any | None = None) -> dict[str, Any]:
    cached = _cache_get("file_support")
    if cached is not None:
        return cached

    if db is not None:
        try:
            rows = _load_module_rows(db, "file_support")
            config = {
                "accepted_extensions": list(_DEFAULT_FILE_SUPPORT["accepted_extensions"]),
                "image_extensions": list(_DEFAULT_FILE_SUPPORT["image_extensions"]),
                "type_map": dict(_DEFAULT_FILE_SUPPORT["type_map"]),
            }
            for row in rows:
                key = str(row.key).strip()
                value_list = row.value_list
                if key in {"accepted_extensions", "image_extensions"} and isinstance(
                    value_list, list
                ):
                    config[key] = [str(v).strip().lower() for v in value_list if str(v).strip()]
                elif key == "type_map" and isinstance(value_list, list):
                    parsed_type_map: dict[str, str] = {}
                    for item in value_list:
                        raw = str(item).strip()
                        if not raw:
                            continue
                        separator = "=" if "=" in raw else ":"
                        ext, _, file_type = raw.partition(separator)
                        ext = ext.strip().lower()
                        file_type = file_type.strip().upper()
                        if ext and file_type:
                            parsed_type_map[ext] = file_type
                    if parsed_type_map:
                        config["type_map"] = parsed_type_map
            return _cache_set("file_support", config)
        except Exception as exc:
            logger.warning("No se pudo cargar file_support desde imp_config: %s", exc)

    return _DEFAULT_FILE_SUPPORT


def load_prompt_config(db: Any | None = None) -> dict[str, Any]:
    cached = _cache_get("prompt_config")
    if cached is not None:
        return cached

    if db is not None:
        try:
            rows = _ensure_module_seeded(db, "prompt_config")
            config = dict(_seed_module_payload("prompt_config"))
            for row in rows:
                key = str(row.key).strip()
                if key in {
                    "extraction_system",
                    "vision_extraction_preamble",
                    "structured_table_note",
                    "doc_type_instruction",
                    "fallback_dynamic_fields_prompt",
                }:
                    value = str(row.value_text or "").strip()
                    if value:
                        config[key] = value
                elif key in {"critical_rules", "vision_critical_rules"} and isinstance(
                    row.value_list, list
                ):
                    values = [str(v).strip() for v in row.value_list if str(v).strip()]
                    if values:
                        config[key] = values
            config["amount_labels"] = load_amount_label_config(db)
            return _cache_set("prompt_config", config)
        except Exception as exc:
            logger.warning("No se pudo cargar prompt_config desde imp_config: %s", exc)

    config = dict(_seed_module_payload("prompt_config"))
    config["amount_labels"] = load_amount_label_config(db)
    return config


def load_classification_threshold(db: Any) -> float:
    """Return the confidence threshold that marks a document as requiring human review.

    Loaded from imp_config(module='classification', key='confidence_threshold').
    Falls back to 0.85 when DB is unavailable.
    Cached for 5 minutes junto al resto de runtime config.
    """
    cached = _cache_get("classification")
    if cached is not None:
        return float(
            cached.get(
                "confidence_threshold", _DEFAULT_CLASSIFICATION_CONFIG["confidence_threshold"]
            )
        )

    if db is not None:
        try:
            rows = _load_module_rows(db, "classification")
            config: dict[str, float] = dict(_DEFAULT_CLASSIFICATION_CONFIG)
            for row in rows:
                key = str(row.key or "").strip()
                if key == "confidence_threshold" and row.value_text is not None:
                    try:
                        config[key] = max(0.0, min(1.0, float(row.value_text)))
                    except (TypeError, ValueError):
                        pass
            _cache_set("classification", config)
            return float(config["confidence_threshold"])
        except Exception as exc:
            logger.warning("No se pudo cargar classification desde imp_config: %s", exc)

    return float(_DEFAULT_CLASSIFICATION_CONFIG["confidence_threshold"])


def load_product_sheet_detection_config(db: Any | None = None) -> dict[str, list[str]]:
    cached = _cache_get("product_sheet_detection")
    if cached is not None:
        return cached  # type: ignore[return-value]

    if db is not None:
        try:
            rows = _ensure_module_seeded(db, "product_sheet_detection")
            config = {
                key: list(value)
                for key, value in _seed_module_payload("product_sheet_detection").items()
                if isinstance(value, list)
            }
            for row in rows:
                key = str(row.key).strip()
                if not key or not isinstance(row.value_list, list):
                    continue
                values = [str(v).strip().lower() for v in row.value_list if str(v).strip()]
                if values:
                    config[key] = values
            return _cache_set("product_sheet_detection", config)  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("No se pudo cargar product_sheet_detection desde imp_config: %s", exc)

    return {
        key: list(value)
        for key, value in _seed_module_payload("product_sheet_detection").items()
        if isinstance(value, list)
    }


def load_amount_label_config(db: Any | None = None) -> dict[str, list[str]]:
    cached = _cache_get("amount_label_config")
    if cached is not None:
        return cached  # type: ignore[return-value]

    if db is not None:
        try:
            rows = _ensure_module_seeded(db, "amount_label_config")
            config = {
                key: list(value)
                for key, value in _seed_module_payload("amount_label_config").items()
                if isinstance(value, list)
            }
            for row in rows:
                key = str(row.key).strip()
                if not key or not isinstance(row.value_list, list):
                    continue
                values = [str(v).strip().lower() for v in row.value_list if str(v).strip()]
                if values:
                    config[key] = values
            return _cache_set("amount_label_config", config)  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("No se pudo cargar amount_label_config desde imp_config: %s", exc)

    return {
        key: list(value)
        for key, value in _seed_module_payload("amount_label_config").items()
        if isinstance(value, list)
    }


def load_learning_config(db: Any) -> dict[str, float]:
    """Return pesos y parámetros del algoritmo de aprendizaje de señales.

    Loaded from imp_config(module='learning'). Falls back to hardcoded defaults
    cuando la BD no está disponible. Cacheado 5 min.

    Claves devueltas:
      event_weight_save / confirm / edit / default   — peso por tipo de evento
      quality_bonus_required_fields_ok / no_review_needed / has_destination — bonuses
      filename_pattern_base_confidence               — confianza base para patrones aprendidos
    """
    cached = _cache_get("learning")
    if cached is not None:
        return cached  # type: ignore[return-value]

    if db is not None:
        try:
            rows = _load_module_rows(db, "learning")
            config: dict[str, float] = dict(_DEFAULT_LEARNING_CONFIG)
            for row in rows:
                key = str(row.key or "").strip()
                if key in config and row.value_text is not None:
                    try:
                        config[key] = float(row.value_text)
                    except (TypeError, ValueError):
                        pass
            return _cache_set("learning", config)  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("No se pudo cargar learning config desde imp_config: %s", exc)

    return dict(_DEFAULT_LEARNING_CONFIG)  # type: ignore[return-value]


def load_pdf_table_parse_config(db: Any | None = None) -> dict[str, list[str]]:
    """Configuración para parseo de tablas en OCR de PDFs.

    Cargado desde imp_config(module='pdf_table_parse').  Claves:
      unit_values           — valores que indican unidad de medida en una celda
                              (ej: ml, g, kg). Usados para detectar descripciones
                              multi-línea sin fusionar la abreviatura de unidad.
      footer_skip_patterns  — patrones regex para saltar líneas de pie de página
                              (ej: "pagina 1 de 3").
    """
    cached = _cache_get("pdf_table_parse")
    if cached is not None:
        return cached  # type: ignore[return-value]

    if db is not None:
        try:
            rows = _ensure_module_seeded(db, "pdf_table_parse")
            config = {
                key: list(value)
                for key, value in _seed_module_payload("pdf_table_parse").items()
                if isinstance(value, list)
            }
            for row in rows:
                key = str(row.key).strip()
                if not key or not isinstance(row.value_list, list):
                    continue
                values = [str(v).strip() for v in row.value_list if str(v).strip()]
                if values:
                    config[key] = values
            return _cache_set("pdf_table_parse", config)  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("No se pudo cargar pdf_table_parse desde imp_config: %s", exc)

    return {
        key: list(value)
        for key, value in _seed_module_payload("pdf_table_parse").items()
        if isinstance(value, list)
    }


def invalidate_runtime_config_cache() -> None:
    _cache.clear()
