from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Any

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
from app.models.core.products import Product
from app.models.recipes import Recipe, RecipeIngredient
from app.modules.imports.application.sku_utils import sanitize_sku
from app.modules.imports.application.transform_dsl import _to_number as dsl_to_number
from app.modules.imports.application.transform_dsl import eval_expr
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.parsers import registry as parsers_registry

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


def _parse_month_name_date(s: str) -> date | None:
    txt = str(s or "").strip().lower()
    if not txt:
        return None
    txt = re.sub(r"[,\.\s]+", " ", txt).strip()
    # "August 3 2025" / "Agosto 3 2025"
    m = re.match(r"^([a-zA-Z\u00C0-\u017F]+)\s+(\d{1,2})\s+(\d{4})$", txt)
    if m:
        month = _MONTHS_MAP.get(m.group(1))
        if month:
            try:
                return date(int(m.group(3)), month, int(m.group(2)))
            except Exception:
                return None
    # "3 August 2025" / "3 Agosto 2025"
    m = re.match(r"^(\d{1,2})\s+([a-zA-Z\u00C0-\u017F]+)\s+(\d{4})$", txt)
    if m:
        month = _MONTHS_MAP.get(m.group(2))
        if month:
            try:
                return date(int(m.group(3)), month, int(m.group(1)))
            except Exception:
                return None
    # "August 2025" / "Agosto 2025" -> first day
    m = re.match(r"^([a-zA-Z\u00C0-\u017F]+)\s+(\d{4})$", txt)
    if m:
        month = _MONTHS_MAP.get(m.group(1))
        if month:
            try:
                return date(int(m.group(2)), month, 1)
            except Exception:
                return None
    return None


def _dedupe_hash(obj: dict[str, Any]) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _idempotency_key(tenant_id: str, file_key: str, idx: int) -> str:
    return f"{tenant_id}:{file_key}:{idx}"


def _file_path_from_key(file_key: str) -> str:
    # Local provider: file_key like "imports/{tenant}/{uuid}.xlsx" under uploads/
    if file_key.startswith("imports/"):
        return os.path.join("uploads", file_key.replace("/", os.sep))
    return file_key


def _to_serializable(val):
    """Convert values to JSON-serializable primitives."""
    try:
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
    except Exception:
        # Fallback: stringify unknown types
        try:
            return str(val)
        except Exception:
            return None


def _to_number(val) -> float | None:
    """Convert value to number."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    # Normalize common numeric formats like "1.234,56" and "1,234.56"
    s_norm = re.sub(r"[^0-9,.-]", "", s)
    if "," in s_norm and "." in s_norm:
        if s_norm.rfind(",") > s_norm.rfind("."):
            s_norm = s_norm.replace(".", "").replace(",", ".")
        else:
            s_norm = s_norm.replace(",", "")
    else:
        s_norm = s_norm.replace(",", ".")
    try:
        return float(s_norm)
    except (ValueError, TypeError):
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
    # Numeric regex rescue for mixed OCR text.
    m = re.search(r"(?<!\d)(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})(?!\d)", s_clean)
    if m:
        try:
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mth, d).isoformat()
        except Exception:
            return None
    return None


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


def _extract_invoice_number_from_text(raw: dict[str, Any]) -> str | None:
    """Recover invoice number from noisy OCR text when explicit fields are missing."""
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


def _infer_doc_type_from_record(
    raw: dict[str, Any] | None,
    normalized: dict[str, Any] | None = None,
    fallback: str = "generic",
) -> str:
    """Infer business doc_type from available keys/values when parser returns generic."""
    data: dict[str, Any] = {}
    if isinstance(raw, dict):
        data.update(raw)
    if isinstance(normalized, dict):
        data.update(normalized)
    nmap = {_norm_key(k): v for k, v in data.items() if isinstance(k, str)}

    def has_any(*keys: str) -> bool:
        for key in keys:
            if key in nmap and nmap[key] not in (None, "", []):
                return True
        return False

    if has_any(
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
    ):
        return "invoices"
    if has_any(
        "transaction_date",
        "fecha_operacion",
        "fecha_de_la_operacion",
        "fecha_valor",
        "fecha_de_envio",
        "fecha_envio",
    ) and has_any(
        "amount",
        "importe",
        "importe_ordenado",
        "monto",
        "valor",
        "bank_tx",
    ):
        return "bank_transactions"
    if has_any(
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
    ):
        return "products"
    return fallback


def _norm_key(s: str) -> str:
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
    except Exception:
        return str(s).strip().lower()


def _first_from_raw(raw: dict[str, Any], keys: list[str]) -> Any:
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
    return _first_from_raw(raw, _expand_keys_with_aliases(keys, alias_map))


def _load_dynamic_alias_map(db, tenant_id: str, doc_type: str) -> dict[str, list[str]]:
    """Load aliases configured in tenant_field_configs for imports."""
    try:
        from app.models.core.ui_field_config import TenantFieldConfig  # type: ignore
    except Exception:
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


def _normalize_doc_type(doc_type: str | None) -> str:
    """Mapear alias a doc_type canónico usado por el módulo."""
    if not doc_type:
        return "generic"
    doc = str(doc_type).lower()
    if doc in ("bank", "bank_tx", "bank_transactions"):
        return "bank_transactions"
    if doc in ("invoice", "invoices", "factura", "facturas"):
        return "invoices"
    if doc in ("expense", "expenses", "receipt", "receipts"):
        return "expenses"
    if doc in ("product", "products", "productos"):
        return "products"
    return doc


def _apply_column_mapping(
    raw: dict[str, Any],
    *,
    mapping: dict[str, str] | None,
    transforms: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
            except Exception:
                continue
    if defaults:
        for k, v in defaults.items():
            if k not in base or base[k] in (None, ""):
                base[k] = v
    return base or None


def _extract_items_from_parsed_result(
    parsed_result: dict[str, Any], doc_type: str
) -> list[dict[str, Any]]:
    """Extract items list from parser result based on doc_type."""
    # If parser embeds items in a top-level key, unwrap first
    if doc_type == "products":
        return parsed_result.get("products", parsed_result.get("rows", [parsed_result]))
    elif doc_type == "invoices":
        return parsed_result.get(
            "invoices",
            parsed_result.get("documents", parsed_result.get("rows", [parsed_result])),
        )
    elif doc_type == "bank_transactions":
        return parsed_result.get(
            "bank_transactions",
            parsed_result.get(
                "transactions",
                parsed_result.get("rows", [parsed_result]),
            ),
        )
    elif doc_type == "recipes":
        return parsed_result.get("recipes", [parsed_result])
    elif "rows" in parsed_result:
        return parsed_result["rows"]
    else:
        return [parsed_result]


def _unwrap_wrapped_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Unwrap accidental parser envelope rows: {'rows':[...], 'headers':...}."""
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
    """Skip footer/blank rows that only introduce validation noise."""
    if not isinstance(raw, dict):
        return False

    ignored = {"_row", "_sheet", "_imported_at", "_metadata", "metadata"}
    values = [v for k, v in raw.items() if k not in ignored]
    non_empty = [v for v in values if v not in (None, "", "NaT")]
    if not non_empty:
        return False

    if item_doc_type in ("products", "product"):
        if _first_from_raw(
            raw, ["name", "nombre", "producto", "articulo", "sku", "codigo", "code"]
        ):
            return True
        # Keep row only if it has a meaningful numeric payload.
        nums = [
            _to_number(
                _first_from_raw(
                    raw, ["price", "precio", "cost", "costo", "stock", "cantidad", "existencia"]
                )
            )
        ]
        return any(n not in (None, 0.0) for n in nums)

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


def _build_canonical_from_item(
    raw: dict[str, Any],
    normalized: dict[str, Any],
    doc_type: str,
    parser_id: str,
    alias_map: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    Construir CanonicalDocument a partir de un item parseado.

    Mapea segun doc_type (products, invoices, bank_transactions) al esquema SPEC-1.
    """

    def pick(keys: list[str]) -> Any:
        return _first_from_raw_with_aliases(raw, keys, alias_map)

    if doc_type == "invoices":
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
        issue_date = (
            raw.get("issue_date")
            or raw.get("invoice_date")
            or raw.get("date")
            or pick(["issue_date", "invoice_date", "date", "fecha", "fecha_emision"])
        )
        issue_date = _to_iso_date(issue_date) or _first_date_from_text(raw)
        totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
        subtotal = totals.get("subtotal")
        tax = totals.get("tax")
        total = totals.get("total")
        if subtotal is None:
            subtotal = _to_number(
                pick(["subtotal", "sub_total", "neto", "amount_subtotal", "base"])
            )
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
            base = (
                f"{issue_date or ''}|{total or ''}|"
                f"{pick(['vendor', 'proveedor', 'supplier', 'customer', 'cliente']) or ''}"
            )
            if base.strip("|"):
                invoice_number = (
                    f"AUTO-{hashlib.sha256(base.encode('utf-8')).hexdigest()[:10].upper()}"
                )

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
                "totals": raw.get("totals")
                or {
                    "subtotal": subtotal,
                    "tax": tax,
                    "total": total,
                },
                "lines": raw.get("lines"),
                "currency": raw.get("currency", "USD"),
                "payment": raw.get("payment"),
                "source": raw.get("source", "parser"),
                "confidence": raw.get("confidence", 0.7),
            }
        )

    elif doc_type == "bank_transactions":
        tx_date = (
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
        tx_date = _to_iso_date(tx_date) or _first_date_from_text(raw)
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

    elif doc_type == "recipes":
        return {
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
        }

    elif doc_type in ("products", "product"):
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
            normalized.get("category")
            or normalized.get("categoria")
            or pick(["category", "categoria"])
        )
        sku = (
            normalized.get("sku")
            or normalized.get("codigo")
            or pick(["sku", "codigo", "code", "cod"])
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
                "doc_type_detected": doc_type,
                "raw_data": raw,
            },
            "source": "parser",
            "confidence": raw.get("confidence", 0.5),
        }
    else:  # generic or other
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


def _find_product_by_name(db, tenant_id: str, name: str) -> Product | None:
    try:
        return (
            db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                Product.name.ilike(name),
            )
            .first()
        )
    except Exception:
        return None


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
    product = Product(
        tenant_id=tenant_id,
        name=normalized,
        description=description,
        category=category,
        active=True,
        unit="unit",
    )
    db.add(product)
    db.flush()
    return product, True


def _persist_recipes(db, tenant_id: str, parsed_result: dict[str, Any]) -> dict[str, int]:
    recipes_data = parsed_result.get("recipes", [])
    ingredients_rows = parsed_result.get("rows", [])
    materials_rows = parsed_result.get("materials", [])
    created = 0
    errors = 0
    created_ingredients = 0
    created_materials = 0
    auto_products = 0

    for recipe_data in recipes_data:
        name = recipe_data.get("name")
        if not name:
            errors += 1
            continue

        product, auto_created = _get_or_create_product(
            db, tenant_id, name, description=recipe_data.get("recipe_type")
        )
        if auto_created:
            auto_products += 1

        if not product:
            errors += 1
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

        recipe_ingredients = [row for row in ingredients_rows if row.get("recipe_name") == name]
        for idx, ing in enumerate(recipe_ingredients):
            prod, auto_created_ing = _get_or_create_product(
                db, tenant_id, ing.get("ingredient", ""), category=recipe_data.get("classification")
            )
            if auto_created_ing:
                auto_products += 1
            if not prod:
                errors += 1
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
            created_ingredients += 1

        # Persist materials as additional ingredients (tagged in notes)
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
                auto_products += 1
            if not prod:
                errors += 1
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
            created_materials += 1
        created += 1

    db.commit()
    return {
        "created": created,
        "errors": errors,
        "ingredients": created_ingredients,
        "materials": created_materials,
        "auto_products": auto_products,
    }


@celery_app.task(name="imports.import_file", bind=True)
def import_file(self, *, tenant_id: str, batch_id: str, file_key: str, parser_id: str):
    """Generic file import task using registered parsers.

    - Uses parser registry to dispatch to appropriate parser
    - Creates CanonicalDocument from parser output
    - Validates via validate_canonical
    - Persists parser_id y canonical_doc en ImportItems
    - Creates ImportItems in batches
    """
    file_path = _file_path_from_key(file_key)

    # Get parser from registry
    parser_info = parsers_registry.get_parser(parser_id)
    if not parser_info:
        raise RuntimeError(f"parser_not_found: {parser_id}")

    parser_func = parser_info["handler"]
    doc_type = parser_info["doc_type"]

    # Progress tracking
    processed = 0
    created = 0
    BATCH_SIZE = 1000

    with session_scope() as db:
        # Fix tenant GUC for RLS-aware backends
        try:
            set_tenant_guc(db, str(tenant_id), persist=False)
        except Exception:
            pass

        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            raise RuntimeError("batch_not_found")

        # Persistir parser_id elegido en batch
        batch.parser_id = parser_id
        batch.status = "PARSING"
        db.add(batch)
        db.commit()

        try:
            # Call parser
            parsed_result = parser_func(file_path)
            effective_parser_id = parser_id
            # Si el parser devolvió un tipo detectado, úsalo cuando el parser sea genérico
            detected_doc_type = (
                parsed_result.get("detected_type")
                or parsed_result.get("doc_type")
                or parser_info.get("doc_type")
            )
            doc_type = _normalize_doc_type(detected_doc_type)
            if doc_type == "generic":
                inferred_doc = _infer_doc_type_from_record(
                    parsed_result if isinstance(parsed_result, dict) else None,
                    parsed_result if isinstance(parsed_result, dict) else None,
                    fallback="generic",
                )
                if inferred_doc != "generic":
                    doc_type = inferred_doc
            batch.source_type = batch.source_type or doc_type

            # Special handling for recipes: persist to Recipe/RecipeIngredient
            if doc_type == "recipes":
                persisted = _persist_recipes(db, tenant_id, parsed_result)
                batch.status = "READY" if persisted["errors"] == 0 else "PARTIAL"
                db.add(batch)
                db.commit()
                return {"ok": True, **persisted, "doc_type": doc_type, "parser_id": parser_id}

            # Optional column mapping (ImportColumnMapping)
            mapping_cfg = None
            mapping_transforms = None
            mapping_defaults = None
            mapping_row = None
            try:
                if getattr(batch, "mapping_id", None):
                    from app.models.imports import ImportColumnMapping  # type: ignore

                    cm = (
                        db.query(ImportColumnMapping)
                        .filter(ImportColumnMapping.id == batch.mapping_id)
                        .first()
                    )
                    if cm:
                        mapping_row = cm
                        mapping_cfg = cm.mapping or cm.mappings or {}
                        mapping_transforms = getattr(cm, "transforms", None) or {}
                        mapping_defaults = getattr(cm, "defaults", None) or {}
            except Exception:
                mapping_cfg = mapping_transforms = mapping_defaults = None

            # Create ImportItems from parsed data
            idx_base = db.query(ImportItem).filter(ImportItem.batch_id == batch_id).count() or 0
            idx = idx_base
            buffer: list[ImportItem] = []

            # Extract items from parsed result based on parser type
            items_data = _extract_items_from_parsed_result(parsed_result, doc_type)
            # Fallback: if a specialized Excel parser returns zero rows, retry with generic parser.
            if (
                len(items_data) == 0
                and effective_parser_id != "generic_excel"
                and str(file_path).lower().endswith((".xlsx", ".xls", ".xlsm", ".xlsb"))
            ):
                generic_info = parsers_registry.get_parser("generic_excel")
                if generic_info and callable(generic_info.get("handler")):
                    try:
                        generic_result = generic_info["handler"](file_path)
                        generic_doc_type = _normalize_doc_type(
                            generic_result.get("detected_type")
                            or generic_result.get("doc_type")
                            or generic_info.get("doc_type")
                        )
                        generic_items = _extract_items_from_parsed_result(
                            generic_result, generic_doc_type
                        )
                        if len(generic_items) > 0:
                            parsed_result = generic_result
                            items_data = generic_items
                            doc_type = generic_doc_type
                            effective_parser_id = "generic_excel"
                    except Exception:
                        pass
            if doc_type == "generic" and items_data:
                sample = items_data[0] if isinstance(items_data[0], dict) else None
                inferred_doc = _infer_doc_type_from_record(sample, sample, fallback="generic")
                if inferred_doc != "generic":
                    doc_type = inferred_doc
            if batch.parser_id != effective_parser_id or (batch.source_type or "") != (
                doc_type or ""
            ):
                batch.parser_id = effective_parser_id
                batch.source_type = doc_type or batch.source_type
                db.add(batch)
                db.commit()

            alias_cache: dict[str, dict[str, list[str]]] = {}

            items_validated = 0
            items_failed = 0
            mapping_applied_count = 0

            for item_data in items_data:
                processed += 1
                idx += 1

                # Normalize data for ImportItem
                raw = item_data if isinstance(item_data, dict) else {"value": item_data}
                raw = _unwrap_wrapped_item(raw)
                mapped = None
                if mapping_cfg:
                    mapped = _apply_column_mapping(
                        raw,
                        mapping=mapping_cfg,
                        transforms=mapping_transforms,
                        defaults=mapping_defaults,
                    )
                    if mapped:
                        mapping_applied_count += 1
                normalized = _to_serializable(mapped or raw)
                item_doc_type = doc_type
                if item_doc_type == "generic":
                    item_doc_type = _infer_doc_type_from_record(raw, normalized, fallback=doc_type)
                if not _is_meaningful_row(raw, item_doc_type):
                    continue
                aliases_for_item = alias_cache.get(item_doc_type)
                if aliases_for_item is None:
                    aliases_for_item = _load_dynamic_alias_map(db, str(tenant_id), item_doc_type)
                    alias_cache[item_doc_type] = aliases_for_item

                if item_doc_type == "products":
                    sku_val = (
                        normalized.get("sku") or normalized.get("codigo") or normalized.get("code")
                    )
                    sku_val = sanitize_sku(sku_val)
                    if sku_val:
                        normalized["sku"] = sku_val

                # Add metadata
                normalized["_metadata"] = {
                    "parser": effective_parser_id,
                    "doc_type": item_doc_type,
                    "_imported_at": raw.get("_imported_at", datetime.utcnow().isoformat()),
                    "mapping_applied": bool(mapped),
                }

                # Construir documento canónico basado en doc_type
                canonical_doc = _build_canonical_from_item(
                    raw=raw,
                    normalized=normalized,
                    doc_type=item_doc_type,
                    parser_id=effective_parser_id,
                    alias_map=aliases_for_item,
                )

                # Validar documento canónico
                is_valid, errors = validate_canonical(canonical_doc)

                idem = _idempotency_key(str(tenant_id), file_key, idx)
                dedupe = _dedupe_hash({"normalized": normalized, "doc_type": item_doc_type})

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
                buffer.append(import_item)

                if is_valid:
                    items_validated += 1
                else:
                    items_failed += 1

                if len(buffer) >= BATCH_SIZE:
                    db.add_all(buffer)
                    db.commit()
                    created += len(buffer)
                    buffer.clear()
                    # Report progress
                    try:
                        self.update_state(
                            state=states.STARTED,
                            meta={
                                "processed": processed,
                                "created": created,
                                "validated": items_validated,
                                "failed": items_failed,
                            },
                        )
                    except Exception:
                        pass

            # Flush remainder
            if buffer:
                db.add_all(buffer)
                db.commit()
                created += len(buffer)

            # Done
            if mapping_row and mapping_applied_count > 0:
                try:
                    mapping_row.use_count = int(getattr(mapping_row, "use_count", 0) or 0) + 1
                    mapping_row.last_used_at = datetime.utcnow()
                    db.add(mapping_row)
                except Exception:
                    pass
            batch.status = "READY" if items_failed == 0 else "PARTIAL"
            db.add(batch)
            db.commit()
            return {
                "ok": True,
                "processed": processed,
                "created": created,
                "validated": items_validated,
                "failed": items_failed,
                "doc_type": doc_type,
                "parser_id": effective_parser_id,
            }

        except Exception as e:
            batch.status = "ERROR"
            db.add(batch)
            db.commit()
            raise RuntimeError(str(e)) from e
