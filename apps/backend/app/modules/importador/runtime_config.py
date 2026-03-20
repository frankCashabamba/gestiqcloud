from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("importador.runtime_config")

_CACHE_TTL = 300.0
_cache: dict[str, tuple[float, dict]] = {}

_DEFAULT_DOC_TYPE_PATTERNS: dict[str, list[str]] = {
    "INVOICE": ["invoice", "factura", "rechnung", "fattura", "fatura", "facture"],
    "RECEIPT": ["receipt", "recibo", "boleta", "ticket", "voucher"],
    "BANK_STATEMENT": ["bank statement", "extracto", "estado de cuenta", "kontoauszug"],
    "PAYROLL": ["payroll", "nomina", "planilla", "lohnabrechnung"],
    "INVENTORY": ["inventory", "inventario", "stock", "price list", "lista precios"],
    "COSTING": ["costing", "costeo", "recipe", "receta", "food cost"],
}

_DEFAULT_FILE_SUPPORT = {
    "accepted_extensions": [
        ".pdf", ".png", ".jpg", ".jpeg", ".heic", ".heif", ".tiff", ".bmp", ".gif",
        ".xlsx", ".xls", ".csv", ".xml", ".txt", ".zip",
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
    from app.models.core.ui_field_config import SectorFieldDefault

    return (
        db.query(SectorFieldDefault)
        .filter(
            SectorFieldDefault.sector == "_system",
            SectorFieldDefault.module == module,
        )
        .all()
    )


def load_doc_type_patterns(db: Any) -> dict[str, list[str]]:
    cached = _cache_get("doc_type_patterns")
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        rows = _load_module_rows(db, "importador.doc_type_patterns")
        patterns: dict[str, list[str]] = {}
        for row in rows:
            if not isinstance(row.options, list):
                continue
            values = [str(value).strip().lower() for value in row.options if str(value).strip()]
            if values:
                patterns[str(row.field).strip().upper()] = values
        if patterns:
            return _cache_set("doc_type_patterns", patterns)  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("No se pudo cargar importador.doc_type_patterns desde BD: %s", exc)

    return _DEFAULT_DOC_TYPE_PATTERNS


def load_file_support_config(db: Any | None = None) -> dict[str, Any]:
    cached = _cache_get("file_support")
    if cached is not None:
        return cached

    if db is not None:
        try:
            rows = _load_module_rows(db, "importador.file_support")
            config = {
                "accepted_extensions": list(_DEFAULT_FILE_SUPPORT["accepted_extensions"]),
                "image_extensions": list(_DEFAULT_FILE_SUPPORT["image_extensions"]),
                "type_map": dict(_DEFAULT_FILE_SUPPORT["type_map"]),
            }
            for row in rows:
                key = str(row.field).strip()
                options = row.options
                if key in {"accepted_extensions", "image_extensions"} and isinstance(options, list):
                    config[key] = [
                        str(value).strip().lower()
                        for value in options
                        if str(value).strip()
                    ]
                elif key == "type_map":
                    if isinstance(options, dict):
                        config["type_map"] = {
                            str(ext).strip().lower(): str(file_type).strip().upper()
                            for ext, file_type in options.items()
                            if str(ext).strip() and str(file_type).strip()
                        }
                    elif isinstance(options, list):
                        parsed_type_map: dict[str, str] = {}
                        for item in options:
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
            logger.warning("No se pudo cargar importador.file_support desde BD: %s", exc)

    return _DEFAULT_FILE_SUPPORT


def invalidate_runtime_config_cache() -> None:
    _cache.clear()
