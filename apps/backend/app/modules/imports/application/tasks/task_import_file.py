"""
File import task with improved architecture.

This module provides a Celery task for importing files using registered parsers.
Key improvements:
- Structured logging for debugging
- Simplified main function through extraction of helper functions
- Unified document type classification logic
- Type hints with TypedDict for better type safety
- Optimized product search queries
- Centralized date handling
- Improved alias caching
- Optimized validation and deduplication
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, NamedTuple

from celery import states

try:
    from app.modules.imports.application.celery_app import celery_app
except Exception:  # pragma: no cover
    celery_app = None  # type: ignore

from datetime import date, time
from decimal import Decimal

from app.config.database import session_scope
from app.db.rls import set_tenant_guc
from app.models.core.modelsimport import ImportBatch, ImportItem
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.recipes import Recipe, RecipeIngredient
from app.modules.imports.application.sku_utils import sanitize_sku
from app.modules.imports.application.transform_dsl import _to_number as dsl_to_number
from app.modules.imports.application.transform_dsl import eval_expr
from app.modules.imports.application.template_engine import (
    TemplateInterpreter,
    TemplateMatcher,
    TemplateV2,
    validate_template,
)
from app.modules.imports.application.template_engine.header_norm import normalize_headers
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.domain.mapping_feedback import MappingFeedback, mapping_learner
from app.modules.imports.parsers import registry as parsers_registry

# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================


class ImportStats(NamedTuple):
    """Statistics for import operations."""

    processed: int
    created: int
    validated: int
    failed: int


class MappingConfig(NamedTuple):
    """Configuration for column mapping."""

    cfg: dict[str, str]
    transforms: dict[str, Any]
    defaults: dict[str, Any]
    row: Any | None
    tpl_v2: TemplateV2 | None = None


class DocumentTypeResult(NamedTuple):
    """Result of document type detection."""

    doc_type: str
    parser_id: str
    parsed_result: dict[str, Any]


# =============================================================================
# Constants
# =============================================================================

_MONTHS_MAP = {
    "january": 1,
    "jan": 1,
    "enero": 1,
    "ene": 1,
    "february": 2,
    "feb": 2,
    "febrero": 2,
    "march": 3,
    "mar": 3,
    "marzo": 3,
    "april": 4,
    "apr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "june": 6,
    "jun": 6,
    "junio": 6,
    "july": 7,
    "jul": 7,
    "julio": 7,
    "august": 8,
    "aug": 8,
    "agosto": 8,
    "ago": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "septiembre": 9,
    "setiembre": 9,
    "october": 10,
    "oct": 10,
    "octubre": 10,
    "november": 11,
    "nov": 11,
    "noviembre": 11,
    "december": 12,
    "dec": 12,
    "diciembre": 12,
    "dic": 12,
}

DOC_TYPE_ALIASES = {
    "bank": "bank_transactions",
    "bank_tx": "bank_transactions",
    "invoice": "invoices",
    "factura": "invoices",
    "facturas": "invoices",
    "expense": "expenses",
    "expenses": "expenses",
    "receipt": "expenses",
    "receipts": "expenses",
    "product": "products",
    "productos": "products",
    "recipe": "recipes",
    "receta": "recipes",
    "recetas": "recipes",
}

BATCH_SIZE = 1000
PRODUCT_SEARCH_LIMIT = 200  # Reduced from 2000 for better performance
FUZZY_SIMILARITY_THRESHOLD = 0.88
PRODUCT_NAME_MIN_LENGTH = 4

# Keys for detecting document types
INVOICE_KEYS = [
    "invoice_number",
    "num_factura",
    "numero_factura",
    "nro_factura",
    "folio",
    "comprobante",
    "total_pagar",
    "amount_total",
    "amount_subtotal",
    "totals",
]

BANK_TRANSACTION_KEYS = [
    "transaction_date",
    "fecha_operacion",
    "fecha_de_la_operacion",
    "fecha_valor",
    "fecha_de_envio",
    "fecha_envio",
]

BANK_AMOUNT_KEYS = [
    "amount",
    "importe",
    "importe_ordenado",
    "monto",
    "valor",
    "bank_tx",
]

PRODUCT_KEYS = [
    "sku",
    "codigo",
    "code",
    "name",
    "nombre",
    "articulo",
    "producto",
    "stock",
    "existencia",
    "existencias",
    "price",
    "precio",
    "cost_price",
    "costo_promedio",
]

# =============================================================================
# Date Parsing Utilities
# =============================================================================


def _parse_month_name_date(s: str) -> date | None:
    """Parse dates with month names (e.g., 'August 3 2025', 'Agosto 3 2025')."""
    txt = str(s or "").strip().lower()
    if not txt:
        return None
    txt = re.sub(r"[,\.\s]+", " ", txt).strip()

    # Pattern: "August 3 2025" / "Agosto 3 2025"
    patterns = [
        (r"^([a-zA-Z\u00C0-\u017F]+)\s+(\d{1,2})\s+(\d{4})$", (3, 1, 2)),
        (r"^(\d{1,2})\s+([a-zA-Z\u00C0-\u017F]+)\s+(\d{4})$", (2, 1, 3)),
        (r"^([a-zA-Z\u00C0-\u017F]+)\s+(\d{4})$", (2, None, 1)),
    ]

    for pattern, order in patterns:
        m = re.match(pattern, txt)
        if m:
            month = _MONTHS_MAP.get(m.group(1))
            if month:
                try:
                    y_idx, d_idx, m_idx = order
                    year = int(m.group(y_idx))
                    day = int(m.group(d_idx)) if d_idx else 1
                    return date(year, month, day)
                except Exception:
                    logger.debug(f"Failed to parse date from '{s}': invalid date values")
                    return None
    return None


def _to_iso_date(val: Any) -> str | None:
    """Parse common date formats and return ISO YYYY-MM-DD."""
    if val is None:
        return None
    if isinstance(val, datetime | date):
        try:
            return val.date().isoformat() if isinstance(val, datetime) else val.isoformat()
        except Exception:
            return None

    s = str(val).strip()
    if not s:
        return None

    s_clean = s.replace(",", "").strip()
    date_formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%Y.%m.%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%B %Y",
        "%b %Y",
    )

    for candidate in (s_clean, re.split(r"\s+", s_clean)[0]):
        for fmt in date_formats:
            try:
                dt = datetime.strptime(candidate, fmt).date()
                return dt.isoformat()
            except Exception:
                continue

    parsed = _parse_month_name_date(s_clean)
    if parsed:
        return parsed.isoformat()

    # Numeric regex rescue for mixed OCR text
    m = re.search(r"(?<!\d)(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})(?!\d)", s_clean)
    if m:
        try:
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mth, d).isoformat()
        except Exception:
            logger.debug(f"Failed to parse date from numeric pattern in '{s}'")
            return None
    return None


def _extract_and_normalize_date(
    raw: dict[str, Any], alias_map: dict[str, list[str]] | None, keys: list[str]
) -> str | None:
    """Extract and normalize a date from multiple possible keys."""
    value = _first_from_raw_with_aliases(raw, keys, alias_map)
    return _to_iso_date(value) or _first_date_from_text(raw)


def _first_date_from_text(raw: dict[str, Any]) -> str | None:
    """Extract first probable date from free text values."""
    if not isinstance(raw, dict):
        return None
    for v in raw.values():
        if v in (None, ""):
            continue
        iso = _to_iso_date(v)
        if iso:
            return iso
    return None


# =============================================================================
# Data Conversion Utilities
# =============================================================================


def _to_number(val) -> float | None:
    """Convert value to number, handling common international formats."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None

    # Normalize formats like "1.234,56" (European) and "1,234.56" (US)
    s_norm = re.sub(r"[^0-9,.-]", "", s)
    if "," in s_norm and "." in s_norm:
        # Determine format by position of last separator
        if s_norm.rfind(",") > s_norm.rfind("."):
            # European: "1.234,56"
            s_norm = s_norm.replace(".", "").replace(",", ".")
        else:
            # US: "1,234.56"
            s_norm = s_norm.replace(",", "")
    else:
        s_norm = s_norm.replace(",", ".")

    try:
        return float(s_norm)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to convert '{val}' to number: {e}")
        return None


def _json_safe(value: Any) -> Any:
    """Recursively convert values to JSON-safe primitives."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return _to_serializable(value)


def _to_serializable(val: Any) -> Any:
    """Convert values to JSON-serializable primitives."""
    try:
        if isinstance(val, dict):
            return {str(k): _to_serializable(v) for k, v in val.items()}
        if isinstance(val, (list, tuple, set)):
            return (
                [_to_serializable(v) for v in val]
                if isinstance(val, (list, set))
                else [_to_serializable(v) for v in val]
            )
        if isinstance(val, datetime | date | time):
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        # Numpy scalar types -> Python scalars
        try:
            import numpy as np  # type: ignore

            if isinstance(val, np.integer):
                return int(val)
            if isinstance(val, np.floating):
                return float(val)
            if isinstance(val, np.bool_):
                return bool(val)
        except Exception:
            pass
        return val
    except Exception as e:
        logger.debug(f"Failed to serialize value: {e}")
        try:
            return str(val)
        except Exception:
            return None


# =============================================================================
# Hash and Key Utilities
# =============================================================================


def _dedupe_hash(obj: dict[str, Any]) -> str:
    """Generate SHA256 hash for deduplication."""
    s = json.dumps(_json_safe(obj), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _idempotency_key(tenant_id: str, file_key: str, idx: int) -> str:
    """Generate idempotency key for preventing duplicate imports."""
    return f"{tenant_id}:{file_key}:{idx}"


def _file_path_from_key(file_key: str) -> str:
    """Convert file_key to actual file path."""
    if file_key.startswith("imports/"):
        return os.path.join("uploads", file_key.replace("/", os.sep))
    return file_key


# =============================================================================
# Key Normalization and Lookup
# =============================================================================


def _norm_key(s: str) -> str:
    """Normalize key to lowercase, remove accents, replace special chars with underscores."""
    try:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.strip().lower()
        out = []
        prev_underscore = False
        for ch in s:
            if ch.isalnum():
                out.append(ch)
                prev_underscore = False
            else:
                if not prev_underscore:
                    out.append("_")
                    prev_underscore = True
        return "".join(out).strip("_")
    except Exception as e:
        logger.warning(f"Failed to normalize key '{s}': {e}")
        return str(s).strip().lower()


def _first_from_raw(raw: dict[str, Any], keys: list[str]) -> Any:
    """Get first non-empty value from raw dict using keys."""
    if not isinstance(raw, dict):
        return None
    norm_map = {_norm_key(k): v for k, v in raw.items() if isinstance(k, str)}
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
        nk = _norm_key(key)
        if nk in norm_map and norm_map[nk] not in (None, ""):
            return norm_map[nk]
    return None


def _expand_keys_with_aliases(keys: list[str], alias_map: dict[str, list[str]] | None) -> list[str]:
    """Expand keys with their aliases from the map."""
    if not alias_map:
        return keys
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        candidates = [key, *(alias_map.get(_norm_key(key), []) or [])]
        for candidate in candidates:
            ck = str(candidate).strip()
            if not ck:
                continue
            nk = _norm_key(ck)
            if nk in seen:
                continue
            seen.add(nk)
            out.append(ck)
    return out


def _first_from_raw_with_aliases(
    raw: dict[str, Any], keys: list[str], alias_map: dict[str, list[str]] | None
) -> Any:
    """Get first non-empty value from raw dict using keys and their aliases."""
    return _first_from_raw(raw, _expand_keys_with_aliases(keys, alias_map))


# =============================================================================
# Document Type Classification
# =============================================================================


def _normalize_doc_type(doc_type: str | None) -> str:
    """Normalize document type alias to canonical type."""
    if not doc_type:
        return "generic"
    doc = str(doc_type).lower()
    return DOC_TYPE_ALIASES.get(doc, doc)


def _infer_doc_type_from_record(
    raw: dict[str, Any] | None,
    normalized: dict[str, Any] | None = None,
    fallback: str = "generic",
) -> str:
    """Infer business doc_type from available keys/values."""
    data: dict[str, Any] = {}
    if isinstance(raw, dict):
        data.update(raw)
    if isinstance(normalized, dict):
        data.update(normalized)
    nmap = {_norm_key(k): v for k, v in data.items() if isinstance(k, str)}

    def has_any(*keys: str) -> bool:
        return any(key in nmap and nmap[key] not in (None, "", []) for key in keys)

    if has_any(*INVOICE_KEYS):
        return "invoices"
    if has_any(*BANK_TRANSACTION_KEYS) and has_any(*BANK_AMOUNT_KEYS):
        return "bank_transactions"
    if has_any(*PRODUCT_KEYS):
        return "products"
    return fallback


def _determine_document_type(
    batch: ImportBatch,
    parsed_result: dict[str, Any],
    parser_info: dict[str, Any],
    tenant_classification_kw: dict[str, tuple[str, ...]] | None = None,
) -> DocumentTypeResult:
    """
    Determine document type with a unified decision flow.

    Priority:
    1. Batch pre-classification (from analyze, AI, or user)
    2. Parser detection
    3. Database classification keywords
    4. Heuristic inference from record fields

    Returns DocumentTypeResult with doc_type, effective_parser_id, and parsed_result.
    """
    # 1. Check batch pre-classification
    batch_source = _normalize_doc_type(getattr(batch, "source_type", None))
    if batch_source not in ("generic", "unknown", ""):
        logger.debug(f"Using batch pre-classified type: {batch_source}")
        return DocumentTypeResult(
            doc_type=batch_source,
            parser_id=parser_info["id"],
            parsed_result=parsed_result,
        )

    # 2. Use parser detection
    detected = _normalize_doc_type(
        parsed_result.get("detected_type")
        or parsed_result.get("doc_type")
        or parser_info.get("doc_type")
    )
    if detected != "generic":
        logger.debug(f"Using parser detected type: {detected}")
        return DocumentTypeResult(
            doc_type=detected,
            parser_id=parser_info["id"],
            parsed_result=parsed_result,
        )

    # 3. Try database classification keywords
    if tenant_classification_kw and (headers := parsed_result.get("headers")):
        from app.modules.imports.parsers.generic_excel import _detect_document_type

        db_detected = _detect_document_type(headers, tenant_classification_kw)
        if db_detected != "generic":
            logger.debug(f"Using DB keyword detected type: {db_detected}")
            return DocumentTypeResult(
                doc_type=db_detected,
                parser_id=parser_info["id"],
                parsed_result=parsed_result,
            )

    # 4. Fallback to heuristic inference
    sample = parsed_result if isinstance(parsed_result, dict) else {}
    inferred = _infer_doc_type_from_record(sample, sample, fallback="generic")
    logger.debug(f"Using inferred type: {inferred}")
    return DocumentTypeResult(
        doc_type=inferred,
        parser_id=parser_info["id"],
        parsed_result=parsed_result,
    )


def _try_generic_parser_fallback(
    file_path: str,
    effective_parser_id: str,
    tenant_classification_kw: dict[str, tuple[str, ...]] | None,
) -> tuple[str, dict[str, Any], str] | None:
    """
    Try generic parser as fallback when specialized parser returns no results.

    Returns (doc_type, parsed_result, effective_parser_id) or None.
    """
    if effective_parser_id == "generic_excel" or not str(file_path).lower().endswith(
        (".xlsx", ".xls", ".xlsm", ".xlsb")
    ):
        return None

    generic_info = parsers_registry.get_parser("generic_excel")
    if not generic_info or not callable(generic_info.get("handler")):
        return None

    try:
        generic_result = generic_info["handler"](file_path)
        generic_doc_type = _normalize_doc_type(
            generic_result.get("detected_type")
            or generic_result.get("doc_type")
            or generic_info.get("doc_type")
        )

        # Re-classify with DB keywords if available
        if generic_doc_type == "generic" and tenant_classification_kw:
            if headers := generic_result.get("headers"):
                from app.modules.imports.parsers.generic_excel import _detect_document_type

                generic_doc_type = _detect_document_type(headers, tenant_classification_kw)

        # Re-infer if still generic
        if generic_doc_type == "generic":
            sample = generic_result if isinstance(generic_result, dict) else {}
            generic_doc_type = _infer_doc_type_from_record(sample, sample, fallback="generic")

        generic_items = _extract_items_from_parsed_result(generic_result, generic_doc_type)
        if len(generic_items) > 0:
            logger.info(f"Generic parser fallback succeeded with {len(generic_items)} items")
            return (generic_doc_type, generic_result, "generic_excel")
    except Exception as e:
        logger.warning(f"Generic parser fallback failed: {e}")
    return None


# =============================================================================
# Alias Management
# =============================================================================


@lru_cache(maxsize=32)
def _load_dynamic_alias_map_cached(tenant_id: str, doc_type: str) -> str:
    """Cached version of alias map loading - returns JSON string for caching."""
    # This is a wrapper that returns the JSON string for LRU cache
    # The actual loading happens in _load_dynamic_alias_map
    return ""


def _load_dynamic_alias_map(db, tenant_id: str, doc_type: str) -> dict[str, list[str]]:
    """Load aliases configured in tenant_field_configs for imports."""
    try:
        from app.models.core.ui_field_config import TenantFieldConfig  # type: ignore
    except Exception as e:
        logger.warning(f"Could not import TenantFieldConfig: {e}")
        return {}

    module_candidates = [f"imports_{doc_type}", "imports"]
    rows = (
        db.query(TenantFieldConfig)
        .filter(
            TenantFieldConfig.tenant_id == tenant_id,
            TenantFieldConfig.module.in_(module_candidates),
        )
        .all()
    )

    out: dict[str, list[str]] = {}
    for row in rows:
        field = _norm_key(getattr(row, "field", ""))
        if not field:
            continue
        aliases_raw = getattr(row, "aliases", None)
        aliases: list[str] = []
        if isinstance(aliases_raw, list):
            aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]
        elif isinstance(aliases_raw, dict):
            aliases = [str(v).strip() for v in aliases_raw.values() if str(v).strip()]
        elif isinstance(aliases_raw, str):
            aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]
        out[field] = list(dict.fromkeys([*(out.get(field, []) or []), *aliases]))
    return out


def _get_alias_map(
    db, tenant_id: str, doc_type: str, alias_cache: dict[str, dict[str, list[str]]]
) -> dict[str, list[str]]:
    """Get alias map from cache or load it."""
    cache_key = doc_type
    if cache_key not in alias_cache:
        alias_cache[cache_key] = _load_dynamic_alias_map(db, str(tenant_id), doc_type)
    return alias_cache[cache_key]


# =============================================================================
# Column Mapping
# =============================================================================


def _apply_column_mapping(
    raw: dict[str, Any],
    *,
    mapping: dict[str, str] | None,
    transforms: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Apply column mapping, transforms, and defaults to raw data."""
    if not mapping:
        return None
    base: dict[str, Any] = {}
    for src, dst in mapping.items():
        if not dst or str(dst).lower() == "ignore":
            continue
        if src in raw:
            base[dst] = raw.get(src)

    if transforms:
        ctx = dict(base)
        for field, spec in transforms.items():
            try:
                if isinstance(spec, str):
                    val = eval_expr(spec, ctx)
                elif isinstance(spec, dict) and "expr" in spec:
                    val = eval_expr(str(spec.get("expr")), ctx)
                    if spec.get("type") == "number":
                        val = dsl_to_number(val)
                    if spec.get("round") is not None and val is not None:
                        try:
                            val = round(float(val), int(spec.get("round")))
                        except Exception:
                            pass
                else:
                    continue
                if val is not None:
                    base[field] = val
                ctx[field] = base.get(field)
            except Exception as e:
                logger.debug(f"Failed to apply transform for field '{field}': {e}")
                continue

    if defaults:
        for k, v in defaults.items():
            if k not in base or base[k] in (None, ""):
                base[k] = v
    return base or None


def _load_mapping_config(db, batch: ImportBatch) -> MappingConfig:
    """Load column mapping configuration from database."""
    try:
        from app.models.imports import ImportColumnMapping  # type: ignore
        from app.models.core.modelsimport import ImportMapping

        mapping_id = getattr(batch, "mapping_id", None)

        tpl_candidate: TemplateV2 | None = None
        tpl_row = None

        # 1) Column mapping (legacy)
        if mapping_id:
            cm = (
                db.query(ImportColumnMapping).filter(ImportColumnMapping.id == mapping_id).first()
            )
            if cm:
                cfg = cm.mapping or cm.mappings or {}
                transforms = getattr(cm, "transforms", None) or {}
                defaults = getattr(cm, "defaults", None) or {}
                if cfg:
                    # seguimos pero aún permitimos tpl_v2 si está disponible
                    base_cfg = cfg
                else:
                    base_cfg = {}
            else:
                base_cfg = {}
        else:
            base_cfg = {}

        # 2) ImportMapping (Template V2 support)
        q_tpl = db.query(ImportMapping).filter(ImportMapping.tenant_id == batch.tenant_id)
        if getattr(batch, "source_type", None) not in ("generic", "unknown", "", None):
            q_tpl = q_tpl.filter(ImportMapping.source_type == batch.source_type)
        templates = q_tpl.order_by(ImportMapping.created_at.desc()).all()
        tpl_v2_list: list[TemplateV2] = []
        for tpl in templates:
            if isinstance(tpl.mappings, dict) and tpl.mappings.get("template_version") == 2:
                try:
                    tv2 = TemplateV2(**tpl.mappings)
                    tpl_v2_list.append(tv2)
                    if mapping_id and str(tpl.id) == str(mapping_id):
                        tpl_candidate = tv2
                        tpl_row = tpl
                        break
                except Exception:
                    continue
        if tpl_candidate is None and tpl_v2_list:
            filename = getattr(batch, "original_filename", None) or getattr(batch, "origin", "") or ""
            matcher = TemplateMatcher(tpl_v2_list)
            tpl_candidate = matcher.match(filename, "es")
            if tpl_candidate:
                tpl_row = next((t for t in templates if t.mappings == tpl_candidate.model_dump(mode="json")), None)

        if tpl_candidate:
            return MappingConfig(
                cfg=base_cfg,
                transforms=tpl_candidate.transforms or {},
                defaults=tpl_candidate.defaults or {},
                row=tpl_row,
                tpl_v2=tpl_candidate,
            )

        return MappingConfig(cfg=base_cfg, transforms={}, defaults={}, row=None, tpl_v2=None)
    except Exception as e:
        logger.warning(f"Failed to load mapping config: {e}")
        return MappingConfig(cfg={}, transforms={}, defaults={}, row=None, tpl_v2=None)


# =============================================================================
# Item Extraction and Validation
# =============================================================================


def _extract_items_from_parsed_result(
    parsed_result: dict[str, Any], doc_type: str
) -> list[dict[str, Any]]:
    """Extract items list from parser result based on doc_type."""
    extractors = {
        "products": lambda r: r.get("products", r.get("rows", [r])),
        "invoices": lambda r: r.get("invoices", r.get("documents", r.get("rows", [r]))),
        "bank_transactions": lambda r: r.get(
            "bank_transactions",
            r.get("transactions", r.get("rows", [r])),
        ),
        "recipes": lambda r: r.get("recipes", [r]),
    }

    extractor = extractors.get(doc_type)
    if extractor:
        return extractor(parsed_result)
    if "rows" in parsed_result:
        return parsed_result["rows"]
    return [parsed_result]


def _unwrap_wrapped_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Unwrap accidental parser envelope rows."""
    if not isinstance(raw, dict):
        return raw
    rows = raw.get("rows")
    if (
        isinstance(rows, list)
        and len(rows) == 1
        and isinstance(rows[0], dict)
        and {"headers", "metadata", "detected_type"}.intersection(set(raw.keys()))
    ):
        return rows[0]
    return raw


def _is_meaningful_row(raw: dict[str, Any], item_doc_type: str) -> bool:
    """Check if row contains meaningful data (skip footer/blank rows)."""
    if not isinstance(raw, dict):
        return False

    ignored = {"_row", "_sheet", "_imported_at", "_metadata", "metadata"}
    values = [v for k, v in raw.items() if k not in ignored]
    non_empty = [v for v in values if v not in (None, "", "NaT")]
    if not non_empty:
        return False

    if item_doc_type in ("products", "product"):
        return bool(
            _first_from_raw(
                raw, ["name", "nombre", "producto", "articulo", "sku", "codigo", "code"]
            )
        ) or any(
            _to_number(
                _first_from_raw(
                    raw, ["price", "precio", "cost", "costo", "stock", "cantidad", "existencia"]
                )
            )
            not in (None, 0.0)
        )

    if item_doc_type == "bank_transactions":
        has_date = bool(
            _first_from_raw(
                raw,
                [
                    "transaction_date",
                    "issue_date",
                    "value_date",
                    "date",
                    "fecha",
                    "fecha_valor",
                    "fecha_operacion",
                    "fecha de la operacion",
                    "fecha de envio",
                    "fecha_envio",
                ],
            )
        )
        has_amount = _to_number(
            _first_from_raw(raw, ["amount", "importe", "monto", "valor", "debit", "credit"])
        )
        return has_date or has_amount not in (None, 0.0)

    if item_doc_type == "invoices":
        has_date = bool(
            _first_from_raw(raw, ["invoice_date", "issue_date", "date", "fecha", "fecha_emision"])
        )
        has_number = bool(
            _first_from_raw(
                raw, ["invoice_number", "num_factura", "numero_factura", "comprobante", "folio"]
            )
        )
        has_total = _to_number(
            _first_from_raw(raw, ["total", "amount_total", "importe", "monto", "valor_total"])
        )
        return has_date or has_number or has_total not in (None, 0.0)

    return True


# =============================================================================
# Canonical Document Builder
# =============================================================================


def _extract_invoice_number_from_text(raw: dict[str, Any]) -> str | None:
    """Recover invoice number from noisy OCR text."""
    if not isinstance(raw, dict):
        return None
    patterns = (
        r"(?:factura|invoice|n[úu]mero(?:\s+de)?\s+factura|num\.?\s*factura)\s*[:#-]?\s*([A-Z0-9\-\/]{3,})",
        r"\b([A-Z]{1,4}\-?\d{3,})\b",
    )
    for v in raw.values():
        if v in (None, ""):
            continue
        txt = str(v)
        for p in patterns:
            m = re.search(p, txt, flags=re.IGNORECASE)
            if m:
                candidate = (m.group(1) or "").strip()
                if len(candidate) >= 3:
                    return candidate
    return None


def _build_invoice_canonical(
    raw: dict[str, Any],
    normalized: dict[str, Any],
    parser_id: str,
    alias_map: dict[str, list[str]] | None,
) -> dict[str, Any]:
    """Build canonical document for invoices."""

    def pick(keys: list[str]) -> Any:
        return _first_from_raw_with_aliases(raw, keys, alias_map)

    invoice_number = (
        raw.get("invoice_number")
        or raw.get("invoice")
        or raw.get("number")
        or raw.get("numero_factura")
        or raw.get("numero")
        or pick(
            [
                "invoice_number",
                "invoice",
                "number",
                "num_factura",
                "numero_factura",
                "numero",
                "nro",
                "folio",
                "comprobante",
            ]
        )
    )
    if not invoice_number:
        invoice_number = _extract_invoice_number_from_text(raw)

    issue_date_raw = (
        raw.get("issue_date")
        or raw.get("invoice_date")
        or raw.get("date")
        or pick(["issue_date", "invoice_date", "date", "fecha", "fecha_emision"])
    )
    issue_date = _to_iso_date(issue_date_raw) or _first_date_from_text(raw)

    totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
    subtotal = totals.get("subtotal")
    tax = totals.get("tax")
    total = totals.get("total")

    if subtotal is None:
        subtotal = _to_number(pick(["subtotal", "sub_total", "neto", "amount_subtotal", "base"]))
    if tax is None:
        tax = _to_number(pick(["tax", "iva", "impuesto", "amount_tax"]))
    if total is None:
        total = _to_number(
            pick(["total", "total_pagar", "amount_total", "importe", "monto", "valor_total"])
        )

    if subtotal is None and total is not None:
        subtotal = total
    if tax is None:
        tax = 0.0

    if not invoice_number:
        base = f"{issue_date or ''}|{total or ''}|{pick(['vendor', 'proveedor', 'supplier', 'customer', 'cliente']) or ''}"
        if base.strip("|"):
            invoice_number = f"AUTO-{hashlib.sha256(base.encode('utf-8')).hexdigest()[:10].upper()}"

    return (
        raw
        if raw.get("doc_type") == "invoice"
        else {
            "doc_type": "invoice",
            "invoice_number": invoice_number,
            "issue_date": issue_date,
            "due_date": raw.get("due_date"),
            "vendor": raw.get("vendor") or {"name": pick(["vendor", "proveedor", "supplier"])},
            "buyer": raw.get("buyer") or {"name": pick(["buyer", "customer", "cliente"])},
            "totals": raw.get("totals") or {"subtotal": subtotal, "tax": tax, "total": total},
            "lines": raw.get("lines"),
            "currency": raw.get("currency", "USD"),
            "payment": raw.get("payment"),
            "source": raw.get("source", "parser"),
            "confidence": raw.get("confidence", 0.7),
        }
    )


def _build_bank_transaction_canonical(
    raw: dict[str, Any],
    parser_id: str,
    alias_map: dict[str, list[str]] | None,
) -> dict[str, Any]:
    """Build canonical document for bank transactions."""

    def pick(keys: list[str]) -> Any:
        return _first_from_raw_with_aliases(raw, keys, alias_map)

    tx_date_raw = (
        raw.get("transaction_date")
        or raw.get("issue_date")
        or raw.get("value_date")
        or pick(
            [
                "transaction_date",
                "issue_date",
                "value_date",
                "date",
                "fecha",
                "fecha_valor",
                "fecha_operacion",
                "fecha de la operacion",
                "fecha de operacion",
                "fecha de envio",
                "fecha de envío",
                "fecha_envio",
            ]
        )
    )
    tx_date = _to_iso_date(tx_date_raw) or _first_date_from_text(raw)

    tx_amount = _to_number(
        raw.get("amount")
        or raw.get("importe")
        or pick(["amount", "importe", "monto", "valor", "debit", "credit"])
    )
    if tx_amount is None:
        tx_amount = _to_number(pick(["monto debito", "monto credito", "importe ordenado"]))

    direction = raw.get("direction") or ("debit" if (tx_amount or 0) < 0 else "credit")
    iban_val = raw.get("iban") or pick(["iban", "cuenta", "account"])

    return (
        raw
        if raw.get("doc_type") == "bank_tx"
        else {
            "doc_type": "bank_tx",
            "transaction_date": tx_date,
            "issue_date": tx_date,
            "currency": raw.get("currency", "USD"),
            "bank_tx": raw.get(
                "bank_tx",
                {
                    "amount": abs(float(tx_amount)) if tx_amount is not None else None,
                    "direction": direction,
                    "value_date": raw.get("value_date") or tx_date,
                    "narrative": raw.get("narrative")
                    or raw.get("concepto")
                    or pick(["description", "descripcion", "detalle", "concepto"]),
                    "counterparty": raw.get("counterparty")
                    or pick(["beneficiario", "ordenante", "counterparty"]),
                    "external_ref": raw.get("external_ref")
                    or pick(["reference", "referencia", "ref", "id"]),
                },
            ),
            "payment": {"iban": iban_val} if iban_val else {},
            "source": raw.get("source", "parser"),
            "confidence": raw.get("confidence", 0.7),
        }
    )


def _build_product_canonical(
    raw: dict[str, Any],
    normalized: dict[str, Any],
    parser_id: str,
    alias_map: dict[str, list[str]] | None,
) -> dict[str, Any]:
    """Build canonical document for products."""

    def pick(keys: list[str]) -> Any:
        return _first_from_raw_with_aliases(raw, keys, alias_map)

    name = (
        normalized.get("name")
        or normalized.get("nombre")
        or pick(["name", "nombre", "producto", "articulo"])
        or ""
    )
    price = (
        _to_number(
            normalized.get("price")
            or normalized.get("precio")
            or pick(
                [
                    "price",
                    "precio",
                    "venta",
                    "valor",
                    "importe",
                    "precio_unitario",
                    "precio_unitario_venta",
                ]
            )
        )
        or 0.0
    )
    cost = _to_number(
        normalized.get("cost_price")
        or normalized.get("cost")
        or normalized.get("costo")
        or normalized.get("unit_cost")
        or pick(
            [
                "cost_price",
                "cost",
                "costo",
                "unit_cost",
                "costo_promedio",
                "costo promedio",
                "costo_unitario",
                "costo unitario",
            ]
        )
    )
    stock = _to_number(
        normalized.get("stock")
        or normalized.get("cantidad")
        or pick(["stock", "cantidad", "existencia", "existencias", "unidades"])
    )
    category = (
        normalized.get("category") or normalized.get("categoria") or pick(["category", "categoria"])
    )
    sku = (
        normalized.get("sku") or normalized.get("codigo") or pick(["sku", "codigo", "code", "cod"])
    )
    unit = normalized.get("unit") or normalized.get("unidad") or pick(["unit", "unidad", "uom"])

    product_data = {
        "name": str(name).strip(),
        "sku": str(sku).strip() if sku not in (None, "") else None,
        "category": str(category).strip() if category not in (None, "") else None,
        "price": float(price),
        "stock": float(stock) if stock is not None else None,
        "unit": str(unit).strip() if unit not in (None, "") else None,
    }

    if cost is not None:
        product_data["cost_price"] = float(cost)
        product_data["cost"] = float(cost)
        product_data["unit_cost"] = float(cost)

    return {
        "doc_type": "product",
        "product": product_data,
        "metadata": {
            "parser": parser_id,
            "doc_type_detected": "products",
            "raw_data": raw,
        },
        "source": "parser",
        "confidence": raw.get("confidence", 0.5),
    }


def _build_canonical_from_item(
    raw: dict[str, Any],
    normalized: dict[str, Any],
    doc_type: str,
    parser_id: str,
    alias_map: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build canonical document from parsed item based on doc_type."""
    builders = {
        "invoices": lambda: _build_invoice_canonical(raw, normalized, parser_id, alias_map),
        "bank_transactions": lambda: _build_bank_transaction_canonical(raw, parser_id, alias_map),
        "products": lambda: _build_product_canonical(raw, normalized, parser_id, alias_map),
        "recipes": lambda: {
            "doc_type": "product",
            "product": {
                "name": raw.get("name") or normalized.get("name"),
                "category": raw.get("classification"),
                "description": raw.get("recipe_type"),
            },
            "metadata": {
                "parser": parser_id,
                "detected_type": "recipes",
                "raw_data": raw,
            },
            "source": "parser",
            "confidence": raw.get("confidence", 0.6),
        },
    }

    builder = builders.get(doc_type)
    if builder:
        return builder()

    detected = raw.get("doc_type") or raw.get("detected_type") or doc_type
    return {
        "doc_type": detected if detected in ("other",) else "other",
        "metadata": {
            "parser": parser_id,
            "doc_type_detected": detected,
            "raw_data": raw,
        },
        "source": "parser",
        "confidence": raw.get("confidence", 0.5),
    }


# =============================================================================
# Product Search and Management
# =============================================================================


def _normalize_product_name(value: str | None) -> str:
    """Normalize product name for comparison."""
    if not value:
        return ""
    txt = unicodedata.normalize("NFKD", str(value))
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.lower().strip()
    txt = re.sub(r"[^a-z0-9\s]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _normalize_product_tokens(value: str | None) -> list[str]:
    """Normalize product name into tokens for fuzzy matching."""
    base = _normalize_product_name(value)
    if not base:
        return []
    out: list[str] = []
    for tok in base.split(" "):
        if len(tok) > 3 and tok.endswith("s"):
            out.append(tok[:-1])
        else:
            out.append(tok)
    return out


def _is_similar_product_name(left: str | None, right: str | None) -> bool:
    """Check if two product names are similar using fuzzy matching."""
    a_tokens = _normalize_product_tokens(left)
    b_tokens = _normalize_product_tokens(right)
    if not a_tokens or not b_tokens:
        return False

    a = " ".join(a_tokens)
    b = " ".join(b_tokens)

    # Exact match
    if a == b:
        return True

    # Substring match with minimum length check
    if a in b or b in a:
        min_len = min(len(a), len(b))
        max_len = max(len(a), len(b))
        if min_len >= PRODUCT_NAME_MIN_LENGTH and (min_len / max_len) >= 0.6:
            return True

    # Sequence similarity
    if SequenceMatcher(None, a, b).ratio() >= FUZZY_SIMILARITY_THRESHOLD:
        return True

    # Token overlap
    a_set = set(a_tokens)
    b_set = set(b_tokens)
    overlap = len(a_set.intersection(b_set))
    return overlap > 0 and (overlap / max(min(len(a_set), len(b_set)), 1)) >= 0.75


def _find_product_by_name(db, tenant_id: str, name: str) -> Product | None:
    """Find product by name with improved query performance."""
    target = _normalize_product_name(name)
    if not target:
        return None

    try:
        # Fast path: case-insensitive exact match
        by_name_ci = (
            db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                Product.name.ilike(name),
            )
            .first()
        )
        if by_name_ci:
            logger.debug(f"Found exact match for product: {name}")
            return by_name_ci

        # Fuzzy fallback with limited results
        probe = target.split(" ")[0]
        query = db.query(Product).filter(Product.tenant_id == tenant_id)
        if probe:
            query = query.filter(Product.name.ilike(f"%{probe}%"))
        candidates = query.limit(PRODUCT_SEARCH_LIMIT).all()

        for cand in candidates:
            if _normalize_product_name(cand.name) == target:
                logger.debug(f"Found normalized match for product: {name}")
                return cand
            if _is_similar_product_name(cand.name, name):
                logger.debug(f"Found similar product: {cand.name} ~ {name}")
                return cand
    except Exception as e:
        logger.warning(f"Error searching product by name '{name}': {e}")
    return None


def _resolve_or_create_category_id(
    db,
    tenant_id: str,
    category_name: str | None,
) -> str | None:
    """Resolve existing category or create a new one."""
    if not category_name or str(category_name).strip() == "":
        return None

    normalized = str(category_name).strip()
    existing = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.name == normalized,
        )
        .first()
    )
    if existing:
        return existing.id

    created = ProductCategory(
        tenant_id=tenant_id,
        name=normalized,
        description=None,
    )
    db.add(created)
    db.flush()
    logger.debug(f"Created new category: {normalized}")
    return created.id


def _get_or_create_product(
    db,
    tenant_id: str,
    name: str | None,
    *,
    description: str | None = None,
    category: str | None = None,
) -> tuple[Product | None, bool]:
    """Find or create a product by name within a tenant."""
    if not name or str(name).strip() == "":
        return None, False

    normalized = str(name).strip()
    existing = _find_product_by_name(db, tenant_id, normalized)
    if existing:
        return existing, False

    category_id = _resolve_or_create_category_id(db, tenant_id, category)
    product = Product(
        tenant_id=tenant_id,
        name=normalized,
        description=description,
        category_id=category_id,
        active=True,
        price=0.0,
        stock=0.0,
        unit="unit",
    )
    db.add(product)
    db.flush()
    logger.debug(f"Created new product: {normalized}")
    return product, True


def _persist_recipes(
    db,
    tenant_id: str,
    parsed_result: dict[str, Any],
) -> dict[str, int]:
    """Persist recipes from parsed result."""
    recipes_data = parsed_result.get("recipes", [])
    ingredients_rows = parsed_result.get("rows", [])
    materials_rows = parsed_result.get("materials", [])

    stats = {
        "created": 0,
        "errors": 0,
        "ingredients": 0,
        "materials": 0,
        "auto_products": 0,
    }

    for recipe_data in recipes_data:
        name = recipe_data.get("name")
        if not name:
            stats["errors"] += 1
            continue

        product, auto_created = _get_or_create_product(
            db, tenant_id, name, description=recipe_data.get("recipe_type")
        )
        if auto_created:
            stats["auto_products"] += 1

        if not product:
            stats["errors"] += 1
            continue

        recipe = Recipe(
            tenant_id=tenant_id,
            product_id=product.id,
            name=name,
            yield_qty=recipe_data.get("portions") or 1,
            prep_time_minutes=None,
            instructions=None,
            is_active=True,
            total_cost=recipe_data.get("total_ingredients_cost") or 0,
        )
        db.add(recipe)
        db.flush()

        # Process ingredients
        recipe_ingredients = [row for row in ingredients_rows if row.get("recipe_name") == name]
        for idx, ing in enumerate(recipe_ingredients):
            prod, auto_created_ing = _get_or_create_product(
                db, tenant_id, ing.get("ingredient", ""), category=recipe_data.get("classification")
            )
            if auto_created_ing:
                stats["auto_products"] += 1
            if not prod:
                stats["errors"] += 1
                continue
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=prod.id,
                qty=ing.get("quantity") or 0,
                unit=ing.get("unit") or "unit",
                purchase_packaging=None,
                qty_per_package=ing.get("quantity") or 1,
                package_unit=ing.get("unit") or "unit",
                package_cost=ing.get("amount") or 0,
                notes=None,
                line_order=idx,
            )
            db.add(ingredient)
            stats["ingredients"] += 1

        # Process materials
        mats_for_recipe = [row for row in materials_rows if row.get("recipe_name") == name]
        offset = len(recipe_ingredients)
        for m_idx, mat in enumerate(mats_for_recipe):
            prod, auto_created_mat = _get_or_create_product(
                db,
                tenant_id,
                mat.get("description", ""),
                category=recipe_data.get("classification"),
            )
            if auto_created_mat:
                stats["auto_products"] += 1
            if not prod:
                stats["errors"] += 1
                continue
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=prod.id,
                qty=mat.get("quantity") or 0,
                unit=mat.get("purchase_unit") or "unit",
                purchase_packaging="material",
                qty_per_package=mat.get("quantity") or 1,
                package_unit=mat.get("purchase_unit") or "unit",
                package_cost=mat.get("amount") or mat.get("purchase_price") or 0,
                notes="material",
                line_order=offset + m_idx,
            )
            db.add(ingredient)
            stats["materials"] += 1
        stats["created"] += 1

    db.commit()
    return stats


def _build_recipe_preview_items(parsed_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Build recipe preview rows without persisting into production tables."""
    recipes_data = parsed_result.get("recipes", []) or []
    ingredients_rows = parsed_result.get("rows", []) or []
    materials_rows = parsed_result.get("materials", []) or []
    preview_items: list[dict[str, Any]] = []

    for recipe in recipes_data:
        name = recipe.get("name")
        if not name:
            continue

        recipe_ingredients = [r for r in ingredients_rows if r.get("recipe_name") == name]
        recipe_materials = [r for r in materials_rows if r.get("recipe_name") == name]

        preview_items.append(
            {
                "raw": {
                    "recipe": recipe,
                    "ingredients": recipe_ingredients,
                    "materials": recipe_materials,
                },
                "normalized": {
                    "name": name,
                    "nombre": name,
                    "recipe_type": recipe.get("recipe_type"),
                    "classification": recipe.get("classification"),
                    "portions": recipe.get("portions") or 1,
                    "total_ingredients_cost": recipe.get("total_ingredients_cost") or 0,
                    "ingredients_count": len(recipe_ingredients),
                    "materials_count": len(recipe_materials),
                    "doc_type": "recipes",
                },
            }
        )
    return preview_items


# =============================================================================
# Single Item Processing
# =============================================================================


def _process_single_item(
    item_data: Any,
    batch_id: str,
    file_key: str,
    tenant_id: str,
    idx: int,
    doc_type: str,
    effective_parser_id: str,
    mapping_config: MappingConfig,
    alias_map: dict[str, list[str]],
) -> tuple[ImportItem, bool]:
    """
    Process a single item and return the ImportItem with validation status.

    Returns (ImportItem, is_valid)
    """
    # Normalize data
    raw = item_data if isinstance(item_data, dict) else {"value": item_data}
    raw = _unwrap_wrapped_item(raw)

    # Apply mapping if configured
    mapped = None
    if mapping_config.tpl_v2:
        try:
            tpl = mapping_config.tpl_v2
            lang = raw.get("language", "es") if isinstance(raw, dict) else "es"
            headers_raw = list(raw.keys()) if isinstance(raw, dict) else []
            headers_norm = (
                normalize_headers(headers_raw, tpl.header_normalization, lang)
                if headers_raw
                else []
            )
            normalized_row = {h_norm: raw.get(h_raw) for h_norm, h_raw in zip(headers_norm, headers_raw)} if isinstance(raw, dict) else {}
            interpreter = TemplateInterpreter(tpl)
            processed = interpreter.process_rows([normalized_row])
            if processed:
                mapped = processed[0] if len(processed) == 1 else processed
        except Exception as e:
            logger.debug(f"TemplateV2 mapping failed: {e}")
            mapped = None
    elif mapping_config.cfg:
        mapped = _apply_column_mapping(
            raw,
            mapping=mapping_config.cfg,
            transforms=mapping_config.transforms,
            defaults=mapping_config.defaults,
        )

    normalized = _to_serializable(mapped or raw)
    item_doc_type = doc_type
    if item_doc_type == "generic":
        item_doc_type = _infer_doc_type_from_record(raw, normalized, fallback=doc_type)

    # Skip non-meaningful rows
    if not _is_meaningful_row(raw, item_doc_type):
        return None, False

    # Sanitize SKU for products
    if item_doc_type == "products":
        sku_val = normalized.get("sku") or normalized.get("codigo") or normalized.get("code")
        if sku_val:
            normalized["sku"] = sanitize_sku(sku_val)

    # Add metadata
    normalized["_metadata"] = {
        "parser": effective_parser_id,
        "doc_type": item_doc_type,
        "_imported_at": raw.get("_imported_at", datetime.utcnow().isoformat()),
        "mapping_applied": bool(mapped),
    }

    # Build canonical document
    canonical_doc = _build_canonical_from_item(
        raw=raw,
        normalized=normalized,
        doc_type=item_doc_type,
        parser_id=effective_parser_id,
        alias_map=alias_map,
    )

    # Validate canonical document
    is_valid, errors = validate_canonical(canonical_doc)

    # Calculate dedupe hash only if valid
    dedupe = (
        _dedupe_hash({"normalized": normalized, "doc_type": item_doc_type}) if is_valid else None
    )
    idem = _idempotency_key(str(tenant_id), file_key, idx)

    import_item = ImportItem(
        batch_id=batch_id,
        idx=idx,
        raw=raw,
        normalized=normalized,
        canonical_doc=canonical_doc if is_valid else None,
        idempotency_key=idem,
        dedupe_hash=dedupe,
        status="OK" if is_valid else "ERROR_VALIDATION",
        errors=errors if not is_valid else [],
    )

    return import_item, is_valid


# =============================================================================
# Progress Reporting
# =============================================================================


def _report_progress(task_self, stats: ImportStats) -> None:
    """Report progress to Celery task."""
    try:
        task_self.update_state(
            state=states.STARTED,
            meta={
                "processed": stats.processed,
                "created": stats.created,
                "validated": stats.validated,
                "failed": stats.failed,
            },
        )
    except Exception as e:
        logger.debug(f"Failed to report progress: {e}")


# =============================================================================
# Mapping Feedback
# =============================================================================


def _record_mapping_feedback(
    db,
    tenant_id: str,
    doc_type: str,
    mapping_cfg: dict[str, str],
    successful_count: int,
) -> None:
    """Record mapping feedback for machine learning."""
    if not mapping_cfg or successful_count == 0:
        return

    try:
        feedback = MappingFeedback(
            tenant_id=tenant_id,
            doc_type=doc_type,
            headers=list(mapping_cfg.keys()),
        )
        for source_field, canonical_field in mapping_cfg.items():
            if canonical_field and str(canonical_field).lower() != "ignore":
                feedback.mark_field_correct(
                    str(source_field),
                    str(canonical_field),
                    confidence=0.8,
                )
        if feedback.field_feedbacks:
            mapping_learner.record_feedback(feedback)
            logger.debug(f"Recorded mapping feedback for {len(feedback.field_feedbacks)} fields")
    except Exception as e:
        logger.warning(f"Failed to record mapping feedback: {e}")


def _update_mapping_stats(
    db,
    mapping_row: Any,
    applied_count: int,
) -> None:
    """Update mapping usage statistics."""
    if not mapping_row or applied_count == 0:
        return

    try:
        mapping_row.use_count = int(getattr(mapping_row, "use_count", 0) or 0) + 1
        mapping_row.last_used_at = datetime.utcnow()
        db.add(mapping_row)
        logger.debug(f"Updated mapping stats: use_count={mapping_row.use_count}")
    except Exception as e:
        logger.warning(f"Failed to update mapping stats: {e}")


# =============================================================================
# Classification Keywords Loading
# =============================================================================


def _load_classification_keywords(
    db,
    tenant_id: str,
) -> dict[str, tuple[str, ...]] | None:
    """Load classification keywords from database."""
    try:
        from app.modules.imports.config.classification import load_tenant_classification_keywords

        return load_tenant_classification_keywords(db, str(tenant_id))
    except Exception as e:
        logger.debug(f"Failed to load classification keywords: {e}")
        return None


# =============================================================================
# Main Import Task
# =============================================================================


@celery_app.task(name="imports.import_file", bind=True)
def import_file(
    self,
    *,
    tenant_id: str,
    batch_id: str,
    file_key: str,
    parser_id: str,
) -> dict[str, Any]:
    """
    Generic file import task using registered parsers.

    Workflow:
    1. Get parser from registry and validate batch
    2. Load classification keywords from database
    3. Parse file and determine document type
    4. Load column mapping configuration if present
    5. Process each item: apply mapping, build canonical, validate
    6. Persist items in batches with progress reporting
    7. Record mapping feedback for ML

    Returns:
        Dictionary with import statistics
    """
    logger.info(
        f"Starting import file task: batch_id={batch_id}, parser_id={parser_id}, file_key={file_key}"
    )

    file_path = _file_path_from_key(file_key)

    # Get parser from registry
    parser_info = parsers_registry.get_parser(parser_id)
    if not parser_info:
        logger.error(f"Parser not found: {parser_id}")
        raise RuntimeError(f"parser_not_found: {parser_id}")

    parser_func = parser_info["handler"]
    stats = ImportStats(processed=0, created=0, validated=0, failed=0)

    with session_scope() as db:
        # Set tenant GUC for RLS-aware backends
        try:
            set_tenant_guc(db, str(tenant_id), persist=False)
        except Exception as e:
            logger.warning(f"Failed to set tenant GUC: {e}")

        # Get and validate batch
        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            logger.error(f"Batch not found: {batch_id}")
            raise RuntimeError("batch_not_found")

        # Update batch status
        batch.parser_id = parser_id
        batch.status = "PARSING"
        db.add(batch)
        db.commit()

        # Load classification keywords
        tenant_classification_kw = _load_classification_keywords(db, tenant_id)

        try:
            # Call parser
            logger.debug(f"Parsing file: {file_path}")
            parsed_result = parser_func(file_path)
            effective_parser_id = parser_id

            # Determine document type
            doc_result = _determine_document_type(
                batch,
                parsed_result,
                parser_info,
                tenant_classification_kw,
            )
            doc_type = doc_result.doc_type

            # Update batch source type
            if doc_type and doc_type != "generic":
                if not batch.source_type or batch.source_type in ("generic", "unknown", ""):
                    batch.source_type = doc_type
            elif not batch.source_type:
                batch.source_type = doc_type

            # Special handling for recipes
            if doc_type == "recipes":
                items_data = _build_recipe_preview_items(parsed_result)
                created_preview = len(items_data)
                batch.status = "READY" if created_preview > 0 else "EMPTY"
                db.add(batch)
                db.commit()
                logger.info(f"Recipe preview complete: {created_preview} items")
                return {
                    "ok": True,
                    "processed": created_preview,
                    "created": created_preview,
                    "validated": created_preview,
                    "failed": 0,
                    "doc_type": doc_type,
                    "parser_id": parser_id,
                }

            # Load column mapping configuration
            mapping_config = _load_mapping_config(db, batch)

            # Extract items from parsed result
            items_data = _extract_items_from_parsed_result(parsed_result, doc_type)

            # Try generic parser fallback if no items
            if len(items_data) == 0:
                fallback_result = _try_generic_parser_fallback(
                    file_path,
                    effective_parser_id,
                    tenant_classification_kw,
                )
                if fallback_result:
                    doc_type, parsed_result, effective_parser_id = fallback_result
                    items_data = _extract_items_from_parsed_result(parsed_result, doc_type)

                    # Update batch with fallback results
                    batch.parser_id = effective_parser_id
                    batch.source_type = doc_type
                    db.add(batch)
                    db.commit()

            # Re-infer if still generic
            if doc_type == "generic" and items_data:
                sample = items_data[0] if isinstance(items_data[0], dict) else None
                inferred = _infer_doc_type_from_record(sample, sample, fallback="generic")
                if inferred != "generic":
                    doc_type = inferred

            # Prepare for processing
            idx_base = db.query(ImportItem).filter(ImportItem.batch_id == batch_id).count() or 0
            buffer: list[ImportItem] = []
            alias_cache: dict[str, dict[str, list[str]]] = {}
            mapping_applied_count = 0
            successful_mapped_count = 0

            logger.info(f"Processing {len(items_data)} items with doc_type={doc_type}")

            # Process each item
            for item_data in items_data:
                stats = stats._replace(processed=stats.processed + 1)
                idx = idx_base + stats.processed

                # Get alias map
                alias_map = _get_alias_map(db, tenant_id, doc_type, alias_cache)

                # Process item
                import_item, is_valid = _process_single_item(
                    item_data=item_data,
                    batch_id=batch_id,
                    file_key=file_key,
                    tenant_id=tenant_id,
                    idx=idx,
                    doc_type=doc_type,
                    effective_parser_id=effective_parser_id,
                    mapping_config=mapping_config,
                    alias_map=alias_map,
                )

                if import_item is None:
                    continue

                # Update stats
                if is_valid:
                    stats = stats._replace(validated=stats.validated + 1)
                    if mapping_config.cfg:
                        mapping_applied_count += 1
                        successful_mapped_count += 1
                else:
                    stats = stats._replace(failed=stats.failed + 1)

                buffer.append(import_item)

                # Flush buffer when batch size reached
                if len(buffer) >= BATCH_SIZE:
                    db.add_all(buffer)
                    db.commit()
                    stats = stats._replace(created=stats.created + len(buffer))
                    buffer.clear()
                    _report_progress(self, stats)

            # Flush remaining items
            if buffer:
                db.add_all(buffer)
                db.commit()
                stats = stats._replace(created=stats.created + len(buffer))

            # Update mapping statistics
            _update_mapping_stats(db, mapping_config.row, mapping_applied_count)

            # Record mapping feedback
            _record_mapping_feedback(
                db,
                tenant_id,
                doc_type,
                mapping_config.cfg,
                successful_mapped_count,
            )

            # Final batch status update
            batch.status = "READY" if stats.failed == 0 else "PARTIAL"
            db.add(batch)
            db.commit()

            logger.info(
                f"Import complete: processed={stats.processed}, "
                f"created={stats.created}, validated={stats.validated}, failed={stats.failed}"
            )

            return {
                "ok": True,
                "processed": stats.processed,
                "created": stats.created,
                "validated": stats.validated,
                "failed": stats.failed,
                "doc_type": doc_type,
                "parser_id": effective_parser_id,
            }

        except Exception as e:
            logger.exception(f"Error during import: {e}")
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.warning(f"Failed to rollback: {rollback_error}")

            try:
                batch.status = "ERROR"
                db.add(batch)
                db.commit()
            except Exception as status_error:
                logger.warning(f"Failed to update batch status to ERROR: {status_error}")
                try:
                    db.rollback()
                except Exception:
                    pass

            raise RuntimeError(str(e)) from e
