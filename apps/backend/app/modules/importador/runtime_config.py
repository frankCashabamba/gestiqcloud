from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("importador.runtime_config")

_CACHE_TTL: float = float(os.getenv("IMPORTADOR_RUNTIME_CONFIG_TTL", "300"))
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

_DEFAULT_OCR_CONFIG: dict[str, Any] = {
    "min_width": 1800,
    "weak_text_min_words": 4,
    "weak_text_min_chars": 24,
    "pdf_render_dpi": 300,
    "image_contrast": 1.8,
    "image_sharpness": 2.0,
    "tesseract_languages": ["spa", "eng"],
    "primary_psm_modes": ["6", "11"],
    "rescue_psm_modes": ["6"],
    "small_rotation_angles": ["-4", "-2", "2", "4"],
    "primary_variant_labels": [
        "base",
        "base_rot-2",
        "base_rot+2",
        "perspective",
        "perspective_rot-2",
        "perspective_rot+2",
        "autocontrast",
        "autocontrast_rot-2",
        "autocontrast_rot+2",
        "threshold",
        "trimmed",
        "trimmed_rot90",
    ],
    "median_filter_size": 3,
    "perspective_threshold_value": 165,
    "threshold_value": 170,
    "threshold_low_value": 140,
    "trim_background_threshold": 245,
    "trim_min_crop_ratio": 0.35,
    "trim_padding_ratio": 0.03,
    "trim_min_padding_px": 8,
    "perspective_canny_threshold1": 60,
    "perspective_canny_threshold2": 180,
    "perspective_blur_kernel": 5,
    "perspective_kernel_size": 5,
    "perspective_min_area_ratio": 0.18,
    "perspective_min_output_ratio": 0.35,
    "easyocr_languages": ["es", "en"],
    "easyocr_gpu": False,
    "easyocr_enabled": True,
    "easyocr_variant_label": "autocontrast",
    "excel_max_header_scan_rows": 25,
    "excel_max_preview_rows_per_sheet": 120,
    "excel_scan_rows_multiplier": 4,
    "excel_max_text_chars": 4000,
}

_DEFAULT_PRE_CLASSIFIER_CONFIG: dict[str, float] = {
    "min_header_confirmations": 2.0,
    "filename_min_confidence": 0.70,
    "header_coverage_min_ratio": 0.50,
    "structured_skip_threshold": 0.75,
    "ocr_weird_ratio_max": 0.15,
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

    if db is not None:
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


def load_doc_categories_config(db: Any | None = None) -> dict[str, list[str]]:
    cached = _cache_get("doc_categories")
    if cached is not None:
        return cached  # type: ignore[return-value]

    defaults = {
        str(key).strip().lower(): [str(item).upper() for item in value if str(item).strip()]
        for key, value in _seed_module_payload("doc_categories").items()
        if isinstance(value, list)
    }

    if db is None:
        return _cache_set("doc_categories", defaults)  # type: ignore[return-value]

    try:
        rows = _ensure_module_seeded(db, "doc_categories")
        config: dict[str, list[str]] = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip().lower()
            if not key or not isinstance(row.value_list, list):
                continue
            values = [str(item).upper() for item in row.value_list if str(item).strip()]
            if values:
                config[key] = values
        return _cache_set("doc_categories", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar doc_categories desde imp_config: %s", exc)

    return defaults


def load_filename_normalization_config(db: Any | None = None) -> dict[str, list[str]]:
    cached = _cache_get("filename_normalization")
    if cached is not None:
        return cached  # type: ignore[return-value]

    defaults = {
        "uuid_patterns": [],
        "date_patterns": [],
        "long_number_patterns": [],
        "separator_patterns": [],
    }
    seed = _seed_module_payload("filename_normalization")
    if isinstance(seed, dict):
        for key in defaults:
            values = seed.get(key)
            if isinstance(values, list):
                defaults[key] = [str(item) for item in values if str(item).strip()]

    if db is None:
        return _cache_set("filename_normalization", defaults)  # type: ignore[return-value]

    try:
        rows = _ensure_module_seeded(db, "filename_normalization")
        config = {key: list(value) for key, value in defaults.items()}
        for row in rows:
            key = str(row.key or "").strip()
            if key in config and isinstance(row.value_list, list):
                config[key] = [str(item) for item in row.value_list if str(item).strip()]
        return _cache_set("filename_normalization", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar filename_normalization desde imp_config: %s", exc)

    return defaults


def load_tax_id_patterns_config(db: Any | None = None) -> dict[str, Any]:
    cached = _cache_get("tax_id_patterns")
    if cached is not None:
        return cached

    seed = _seed_module_payload("tax_id_patterns")

    def _int_value(value: Any, default: int, *, minimum: int = 1) -> int:
        try:
            return max(minimum, int(str(value).strip()))
        except (TypeError, ValueError):
            return default

    defaults: dict[str, Any] = {
        "match_patterns": [
            str(item) for item in (seed.get("match_patterns") or []) if str(item).strip()
        ],
        "scan_max_chars": _int_value(seed.get("scan_max_chars"), 3000),
        "min_digits": _int_value(seed.get("min_digits"), 8),
        "max_digits": _int_value(seed.get("max_digits"), 15),
    }

    if db is None:
        return _cache_set("tax_id_patterns", defaults)

    try:
        rows = _ensure_module_seeded(db, "tax_id_patterns")
        config = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            if key == "match_patterns" and isinstance(row.value_list, list):
                config[key] = [str(item) for item in row.value_list if str(item).strip()]
            elif key in {"scan_max_chars", "min_digits", "max_digits"} and row.value_text is not None:
                config[key] = _int_value(row.value_text, config[key])
        return _cache_set("tax_id_patterns", config)
    except Exception as exc:
        logger.warning("No se pudo cargar tax_id_patterns desde imp_config: %s", exc)

    return defaults


def load_routing_field_aliases(db: Any | None = None) -> dict[str, tuple[str, ...]]:
    cached = _cache_get("routing_field_aliases")
    if cached is not None:
        return cached  # type: ignore[return-value]

    defaults = {
        str(key).strip(): tuple(str(item).strip() for item in value if str(item).strip())
        for key, value in _seed_module_payload("routing_field_aliases").items()
        if isinstance(value, list)
    }

    if db is None:
        return _cache_set("routing_field_aliases", defaults)  # type: ignore[return-value]

    try:
        rows = _ensure_module_seeded(db, "routing_field_aliases")
        config = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            if key and isinstance(row.value_list, list):
                values = tuple(str(item).strip() for item in row.value_list if str(item).strip())
                if values:
                    config[key] = values
        return _cache_set("routing_field_aliases", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar routing_field_aliases desde imp_config: %s", exc)

    return defaults


def load_routing_field_labels(db: Any | None = None) -> dict[str, str]:
    cached = _cache_get("routing_field_labels")
    if cached is not None:
        return cached  # type: ignore[return-value]

    defaults = {
        str(key).strip(): str(value).strip()
        for key, value in _seed_module_payload("routing_field_labels").items()
        if str(key).strip() and str(value).strip()
    }

    if db is None:
        return _cache_set("routing_field_labels", defaults)  # type: ignore[return-value]

    try:
        rows = _ensure_module_seeded(db, "routing_field_labels")
        config = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            value = str(row.value_text or "").strip()
            if key and value:
                config[key] = value
        return _cache_set("routing_field_labels", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar routing_field_labels desde imp_config: %s", exc)

    return defaults


def load_routing_fallback_profiles_config(db: Any | None = None) -> dict[str, dict[str, Any]]:
    cached = _cache_get("routing_fallback_profiles")
    if cached is not None:
        return cached  # type: ignore[return-value]

    defaults = {
        str(key).strip().upper(): value
        for key, value in _seed_module_payload("routing_fallback_profiles").items()
        if isinstance(value, dict)
    }

    if db is None:
        return _cache_set("routing_fallback_profiles", defaults)  # type: ignore[return-value]

    try:
        rows = _load_module_rows(db, "routing_fallback_profiles")
        config = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip().upper()
            raw = str(row.value_text or "").strip()
            if not key or not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if isinstance(payload, dict):
                config[key] = payload
        return _cache_set("routing_fallback_profiles", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar routing_fallback_profiles desde imp_config: %s", exc)

    return defaults


def load_routing_fallback_rules_config(db: Any | None = None) -> list[dict[str, Any]]:
    cached = _cache_get("routing_fallback_rules")
    if cached is not None:
        return cached  # type: ignore[return-value]

    defaults: list[dict[str, Any]] = []
    seed = _seed_module_payload("routing_fallback_rules")
    if isinstance(seed, dict):
        for values in seed.values():
            if not isinstance(values, list):
                continue
            payload: dict[str, Any] = {}
            for item in values:
                raw = str(item).strip()
                if not raw:
                    continue
                key, _, value = raw.partition("=")
                if not key.strip():
                    continue
                payload[key.strip()] = value.strip()
            if payload:
                defaults.append(payload)

    if db is None:
        return _cache_set("routing_fallback_rules", defaults)  # type: ignore[return-value]

    try:
        rows = _load_module_rows(db, "routing_fallback_rules")
        config = list(defaults)
        for row in rows:
            if isinstance(row.value_list, list):
                payload: dict[str, Any] = {}
                for item in row.value_list:
                    raw = str(item).strip()
                    if not raw:
                        continue
                    key, _, value = raw.partition("=")
                    if key.strip():
                        payload[key.strip()] = value.strip()
                if payload:
                    config.append(payload)
            elif row.value_text:
                try:
                    payload = json.loads(str(row.value_text).strip())
                except Exception:
                    continue
                if isinstance(payload, dict):
                    config.append(payload)
        return _cache_set("routing_fallback_rules", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar routing_fallback_rules desde imp_config: %s", exc)

    return defaults


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


def load_ocr_runtime_config(db: Any | None = None) -> dict[str, Any]:
    cached = _cache_get("ocr_config")
    if cached is not None:
        return cached

    config: dict[str, Any] = {
        "min_width": int(_DEFAULT_OCR_CONFIG["min_width"]),
        "weak_text_min_words": int(_DEFAULT_OCR_CONFIG["weak_text_min_words"]),
        "weak_text_min_chars": int(_DEFAULT_OCR_CONFIG["weak_text_min_chars"]),
        "pdf_render_dpi": int(_DEFAULT_OCR_CONFIG["pdf_render_dpi"]),
        "image_contrast": float(_DEFAULT_OCR_CONFIG["image_contrast"]),
        "image_sharpness": float(_DEFAULT_OCR_CONFIG["image_sharpness"]),
        "tesseract_languages": list(_DEFAULT_OCR_CONFIG["tesseract_languages"]),
        "primary_psm_modes": list(_DEFAULT_OCR_CONFIG["primary_psm_modes"]),
        "rescue_psm_modes": list(_DEFAULT_OCR_CONFIG["rescue_psm_modes"]),
        "small_rotation_angles": list(_DEFAULT_OCR_CONFIG["small_rotation_angles"]),
        "primary_variant_labels": list(_DEFAULT_OCR_CONFIG["primary_variant_labels"]),
        "median_filter_size": int(_DEFAULT_OCR_CONFIG["median_filter_size"]),
        "perspective_threshold_value": int(_DEFAULT_OCR_CONFIG["perspective_threshold_value"]),
        "threshold_value": int(_DEFAULT_OCR_CONFIG["threshold_value"]),
        "threshold_low_value": int(_DEFAULT_OCR_CONFIG["threshold_low_value"]),
        "trim_background_threshold": int(_DEFAULT_OCR_CONFIG["trim_background_threshold"]),
        "trim_min_crop_ratio": float(_DEFAULT_OCR_CONFIG["trim_min_crop_ratio"]),
        "trim_padding_ratio": float(_DEFAULT_OCR_CONFIG["trim_padding_ratio"]),
        "trim_min_padding_px": int(_DEFAULT_OCR_CONFIG["trim_min_padding_px"]),
        "perspective_canny_threshold1": int(_DEFAULT_OCR_CONFIG["perspective_canny_threshold1"]),
        "perspective_canny_threshold2": int(_DEFAULT_OCR_CONFIG["perspective_canny_threshold2"]),
        "perspective_blur_kernel": int(_DEFAULT_OCR_CONFIG["perspective_blur_kernel"]),
        "perspective_kernel_size": int(_DEFAULT_OCR_CONFIG["perspective_kernel_size"]),
        "perspective_min_area_ratio": float(_DEFAULT_OCR_CONFIG["perspective_min_area_ratio"]),
        "perspective_min_output_ratio": float(_DEFAULT_OCR_CONFIG["perspective_min_output_ratio"]),
        "easyocr_languages": list(_DEFAULT_OCR_CONFIG["easyocr_languages"]),
        "easyocr_gpu": bool(_DEFAULT_OCR_CONFIG["easyocr_gpu"]),
        "easyocr_enabled": bool(_DEFAULT_OCR_CONFIG["easyocr_enabled"]),
        "easyocr_variant_label": str(_DEFAULT_OCR_CONFIG["easyocr_variant_label"]),
        "excel_max_header_scan_rows": int(_DEFAULT_OCR_CONFIG["excel_max_header_scan_rows"]),
        "excel_max_preview_rows_per_sheet": int(_DEFAULT_OCR_CONFIG["excel_max_preview_rows_per_sheet"]),
        "excel_scan_rows_multiplier": int(_DEFAULT_OCR_CONFIG["excel_scan_rows_multiplier"]),
        "excel_max_text_chars": int(_DEFAULT_OCR_CONFIG["excel_max_text_chars"]),
    }

    def _int_value(value: Any, default: int, *, minimum: int = 1) -> int:
        try:
            return max(minimum, int(str(value).strip()))
        except (TypeError, ValueError):
            return default

    def _bool_value(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        raw = str(value or "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
        return default

    def _float_value(value: Any, default: float, *, minimum: float | None = None) -> float:
        try:
            parsed = float(str(value).strip())
        except (TypeError, ValueError):
            return default
        if minimum is not None:
            return max(minimum, parsed)
        return parsed

    def _list_value(values: Any, defaults: list[str]) -> list[str]:
        if not isinstance(values, list):
            return list(defaults)
        parsed = [str(value).strip() for value in values if str(value).strip()]
        return parsed or list(defaults)

    seed = _seed_module_payload("ocr_config")
    if isinstance(seed, dict):
        for key, value in seed.items():
            if key in {
                "min_width",
                "pdf_render_dpi",
                "median_filter_size",
                "perspective_threshold_value",
                "threshold_value",
                "threshold_low_value",
                "trim_background_threshold",
                "trim_min_padding_px",
                "perspective_canny_threshold1",
                "perspective_canny_threshold2",
                "perspective_blur_kernel",
                "perspective_kernel_size",
                "excel_max_header_scan_rows",
                "excel_max_preview_rows_per_sheet",
                "excel_scan_rows_multiplier",
                "excel_max_text_chars",
            }:
                config[key] = _int_value(value, config[key])
            elif key in {"weak_text_min_words", "weak_text_min_chars"}:
                config[key] = _int_value(value, config[key], minimum=0)
            elif key in {
                "image_contrast",
                "image_sharpness",
                "trim_min_crop_ratio",
                "trim_padding_ratio",
                "perspective_min_area_ratio",
                "perspective_min_output_ratio",
            }:
                config[key] = _float_value(value, config[key], minimum=0.0)
            elif key in {
                "tesseract_languages",
                "primary_psm_modes",
                "rescue_psm_modes",
                "small_rotation_angles",
                "primary_variant_labels",
                "easyocr_languages",
            }:
                config[key] = _list_value(value, config[key])
            elif key in {"easyocr_enabled", "easyocr_gpu"}:
                config[key] = _bool_value(value, config[key])
            elif key == "easyocr_variant_label":
                parsed = str(value or "").strip()
                if parsed:
                    config[key] = parsed

    if db is not None:
        try:
            rows = _ensure_module_seeded(db, "ocr_config")
            for row in rows:
                key = str(row.key or "").strip()
                if key in {
                    "min_width",
                    "pdf_render_dpi",
                    "median_filter_size",
                    "perspective_threshold_value",
                    "threshold_value",
                    "threshold_low_value",
                    "trim_background_threshold",
                    "trim_min_padding_px",
                    "perspective_canny_threshold1",
                    "perspective_canny_threshold2",
                    "perspective_blur_kernel",
                    "perspective_kernel_size",
                    "excel_max_header_scan_rows",
                    "excel_max_preview_rows_per_sheet",
                    "excel_scan_rows_multiplier",
                    "excel_max_text_chars",
                } and row.value_text is not None:
                    config[key] = _int_value(row.value_text, config[key])
                elif key in {"weak_text_min_words", "weak_text_min_chars"} and row.value_text is not None:
                    config[key] = _int_value(row.value_text, config[key], minimum=0)
                elif key in {
                    "image_contrast",
                    "image_sharpness",
                    "trim_min_crop_ratio",
                    "trim_padding_ratio",
                    "perspective_min_area_ratio",
                    "perspective_min_output_ratio",
                } and row.value_text is not None:
                    config[key] = _float_value(row.value_text, config[key], minimum=0.0)
                elif key in {
                    "tesseract_languages",
                    "primary_psm_modes",
                    "rescue_psm_modes",
                    "small_rotation_angles",
                    "primary_variant_labels",
                    "easyocr_languages",
                }:
                    config[key] = _list_value(row.value_list, config[key])
                elif key in {"easyocr_enabled", "easyocr_gpu"} and row.value_text is not None:
                    config[key] = _bool_value(row.value_text, config[key])
                elif key == "easyocr_variant_label" and row.value_text is not None:
                    parsed = str(row.value_text).strip()
                    if parsed:
                        config[key] = parsed
        except Exception as exc:
            logger.warning("No se pudo cargar ocr_config desde imp_config: %s", exc)

    return _cache_set("ocr_config", config)


def load_pre_classifier_runtime_config(db: Any | None = None) -> dict[str, float]:
    cached = _cache_get("pre_classifier")
    if cached is not None:
        return cached  # type: ignore[return-value]

    config: dict[str, float] = dict(_DEFAULT_PRE_CLASSIFIER_CONFIG)

    def _float_value(value: Any, default: float) -> float:
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return default

    seed = _seed_module_payload("pre_classifier")
    if isinstance(seed, dict):
        for key, value in seed.items():
            if key in config:
                config[key] = _float_value(value, config[key])

    if db is not None:
        try:
            rows = _ensure_module_seeded(db, "pre_classifier")
            for row in rows:
                key = str(row.key or "").strip()
                if key in config and row.value_text is not None:
                    config[key] = _float_value(row.value_text, config[key])
        except Exception as exc:
            logger.warning("No se pudo cargar pre_classifier desde imp_config: %s", exc)

    return _cache_set("pre_classifier", config)  # type: ignore[return-value]


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
                    "vision_system_fallback",
                    "vision_extraction_preamble",
                    "structured_classification_task_preamble",
                    "structured_classification_response_instruction",
                    "structured_classification_preview_label",
                    "structured_table_note",
                    "doc_type_instruction",
                    "response_json_label",
                    "critical_rules_heading",
                    "additional_instructions_heading",
                    "fallback_dynamic_fields_prompt",
                    "year_sanity_rule_template",
                    "line_items_extra_columns_rule",
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


def load_ai_params(db: Any | None = None) -> dict[str, Any]:
    """Parámetros de las llamadas AI (temperatura, max_tokens, content_limit).

    Cargado desde imp_config(module='ai_params'). Permite ajustar el comportamiento
    de Ollama/Claude por tipo de documento sin tocar código.

    Claves:
      temperature                    — float, default 0.1
      max_tokens_extraction          — int, default 1500
      max_tokens_classification      — int, default 220
      content_limit_unstructured     — int, default 7000
      content_limit_structured       — int, default 4000
      max_tokens_by_doctype          — dict {DOC_TYPE: int}, overrides max_tokens_extraction
    """
    cached = _cache_get("ai_params")
    if cached is not None:
        return cached  # type: ignore[return-value]

    seed = _seed_module_payload("ai_params")

    def _int(val: Any, default: int) -> int:
        try:
            return int(str(val).strip())
        except (TypeError, ValueError):
            return default

    def _float(val: Any, default: float) -> float:
        try:
            return max(0.0, min(1.0, float(str(val).strip())))
        except (TypeError, ValueError):
            return default

    defaults: dict[str, Any] = {
        "temperature": _float(seed.get("temperature"), 0.1),
        "max_tokens_extraction": _int(seed.get("max_tokens_extraction"), 1500),
        "max_tokens_classification": _int(seed.get("max_tokens_classification"), 220),
        "content_limit_unstructured": _int(seed.get("content_limit_unstructured"), 7000),
        "content_limit_structured": _int(seed.get("content_limit_structured"), 4000),
        "max_tokens_by_doctype": {},
    }
    # Poblar max_tokens_by_doctype desde el seed (valores como string)
    seed_by_dt = seed.get("max_tokens_by_doctype") or {}
    if isinstance(seed_by_dt, dict):
        for k, v in seed_by_dt.items():
            tok = _int(v, 0)
            if tok > 0:
                defaults["max_tokens_by_doctype"][str(k).upper()] = tok

    if db is None:
        return defaults

    try:
        rows = _ensure_module_seeded(db, "ai_params")
        config: dict[str, Any] = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            if key == "temperature" and row.value_text is not None:
                config["temperature"] = _float(row.value_text, 0.1)
            elif key in {
                "max_tokens_extraction",
                "max_tokens_classification",
                "content_limit_unstructured",
                "content_limit_structured",
            } and row.value_text is not None:
                config[key] = _int(row.value_text, defaults[key])
            elif key == "max_tokens_by_doctype" and isinstance(row.value_list, list):
                # value_list formato: ["INVOICE=1200", "RECEIPT=600"]
                for item in row.value_list:
                    raw = str(item).strip()
                    sep = "=" if "=" in raw else ":"
                    dt, _, tok_s = raw.partition(sep)
                    tok = _int(tok_s, 0)
                    if dt.strip() and tok > 0:
                        config["max_tokens_by_doctype"][dt.strip().upper()] = tok
        return _cache_set("ai_params", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar ai_params desde imp_config: %s", exc)

    return defaults


def load_ai_model_routing(db: Any | None = None) -> dict[str, str]:
    """Modelo AI a usar por tipo de documento.

    Cargado desde imp_config(module='ai_model_routing'). Permite usar modelos
    más pequeños para tipos de documento simples (RECEIPT, EXPENSE) y reservar
    el modelo mayor para documentos complejos (INVOICE, PAYROLL).

    Retorna dict {DOC_TYPE: model_name_string}. Vacío o valor vacío = usa el
    modelo por defecto configurado en el proveedor AI.
    """
    cached = _cache_get("ai_model_routing")
    if cached is not None:
        return cached  # type: ignore[return-value]

    seed = _seed_module_payload("ai_model_routing")
    defaults: dict[str, str] = {
        str(k).upper(): str(v).strip()
        for k, v in (seed or {}).items()
        if v
    }

    if db is None:
        return defaults

    try:
        rows = _ensure_module_seeded(db, "ai_model_routing")
        config: dict[str, str] = dict(defaults)
        for row in rows:
            key = str(row.key or "").upper().strip()
            val = str(row.value_text or "").strip()
            if key:
                config[key] = val  # vacío = usa default del proveedor
        return _cache_set("ai_model_routing", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar ai_model_routing desde imp_config: %s", exc)

    return defaults


def load_learning_control(db: Any | None = None) -> dict[str, Any]:
    """Parámetros de control del learning rerun.

    Cargado desde imp_config(module='learning_control'). Permite habilitar/
    deshabilitar el rerun y ajustar sus condiciones sin tocar código.

    Claves:
      rerun_enabled              — bool, default True
      rerun_min_confidence       — float, umbral de confianza mínimo para disparar rerun
                                   (0.0 = siempre, 1.0 = nunca). Default 0.0
      rerun_max_snapshot_age_days — int, días máximos desde last_updated de la receta.
                                    0 = sin límite. Default 0
      rerun_require_missing_fields — bool, solo hacer rerun si hay campos faltantes.
                                     Default False
    """
    cached = _cache_get("learning_control")
    if cached is not None:
        return cached  # type: ignore[return-value]

    seed = _seed_module_payload("learning_control")

    def _bool(val: Any, default: bool) -> bool:
        if val is None:
            return default
        return str(val).strip().lower() not in {"false", "0", "no", "off"}

    def _float_val(val: Any, default: float) -> float:
        try:
            return float(str(val).strip())
        except (TypeError, ValueError):
            return default

    def _int_val(val: Any, default: int) -> int:
        try:
            return int(str(val).strip())
        except (TypeError, ValueError):
            return default

    defaults: dict[str, Any] = {
        "rerun_enabled": _bool(seed.get("rerun_enabled"), True),
        "rerun_min_confidence": _float_val(seed.get("rerun_min_confidence"), 0.0),
        "rerun_max_snapshot_age_days": _int_val(seed.get("rerun_max_snapshot_age_days"), 0),
        "rerun_require_missing_fields": _bool(seed.get("rerun_require_missing_fields"), False),
    }

    if db is None:
        return defaults

    try:
        rows = _ensure_module_seeded(db, "learning_control")
        config: dict[str, Any] = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            val = row.value_text
            if key == "rerun_enabled":
                config["rerun_enabled"] = _bool(val, True)
            elif key == "rerun_min_confidence":
                config["rerun_min_confidence"] = _float_val(val, 0.0)
            elif key == "rerun_max_snapshot_age_days":
                config["rerun_max_snapshot_age_days"] = _int_val(val, 0)
            elif key == "rerun_require_missing_fields":
                config["rerun_require_missing_fields"] = _bool(val, False)
        return _cache_set("learning_control", config)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar learning_control desde imp_config: %s", exc)

    return defaults


def load_cache_ttls(db: Any | None = None) -> dict[str, float]:
    """TTLs de los cachés en memoria del importador.

    Cargado desde imp_config(module='cache_ttls'). Permite ajustar la duración
    del caché sin deploy.

    Claves (segundos):
      ocr_ttl_seconds              — default 300
      pre_classifier_ttl_seconds   — default 300
      runtime_config_ttl_seconds   — default 300
    """
    # Este loader NO usa _cache_get para evitar recursión: es el que define el TTL.
    # Se lee desde DB una vez al inicio y se guarda en memoria del módulo.
    cached = _cache.get("cache_ttls")
    if cached:
        ts, value = cached
        # Usamos _CACHE_TTL como bootstrap TTL para este loader específico
        if (time.monotonic() - ts) < _CACHE_TTL:
            return value  # type: ignore[return-value]

    seed = _seed_module_payload("cache_ttls")

    def _secs(val: Any, default: float) -> float:
        try:
            return max(30.0, float(str(val).strip()))
        except (TypeError, ValueError):
            return default

    defaults: dict[str, float] = {
        "ocr_ttl_seconds": _secs(seed.get("ocr_ttl_seconds"), 300.0),
        "pre_classifier_ttl_seconds": _secs(seed.get("pre_classifier_ttl_seconds"), 300.0),
        "runtime_config_ttl_seconds": _secs(seed.get("runtime_config_ttl_seconds"), 300.0),
    }

    if db is None:
        _cache["cache_ttls"] = (time.monotonic(), defaults)
        return defaults

    try:
        rows = _ensure_module_seeded(db, "cache_ttls")
        config: dict[str, float] = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            if key in config and row.value_text is not None:
                config[key] = _secs(row.value_text, defaults[key])
        _cache["cache_ttls"] = (time.monotonic(), config)
        # Actualizar el TTL global del módulo para que _cache_get lo use en lo sucesivo
        globals()["_CACHE_TTL"] = config.get("runtime_config_ttl_seconds", _CACHE_TTL)
        return config
    except Exception as exc:
        logger.warning("No se pudo cargar cache_ttls desde imp_config: %s", exc)

    _cache["cache_ttls"] = (time.monotonic(), defaults)
    return defaults


def invalidate_runtime_config_cache() -> None:
    _cache.clear()
