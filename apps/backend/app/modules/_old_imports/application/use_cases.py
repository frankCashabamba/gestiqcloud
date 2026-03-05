from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai.incident import Incident
from app.models.core.modelsimport import (
    ImportAttachment,
    ImportBatch,
    ImportItem,
    ImportItemCorrection,
    ImportLineage,
    ImportMapping,
)
from app.modules.imports.application.ir_builder import IRBuilder
from app.modules.imports.application.photo_utils import (
    exif_auto_orienta,
    guardar_adjunto_bytes,
    ocr_texto,
    parse_texto_banco,
    parse_texto_factura,
    parse_texto_recibo,
)
from app.modules.imports.application.status import ImportBatchStatus, ImportItemStatus
from app.modules.imports.application.template_engine import (
    TemplateInterpreter,
    TemplateMatcher,
    TemplateV2,
    validate_template,
)
from app.modules.imports.application.template_engine.header_norm import normalize_headers
from app.modules.imports.domain.handlers import (
    BankHandler,
    ExpenseHandler,
    InvoiceHandler,
    ProductHandler,
    RecipeHandler,
)
from app.modules.imports.infrastructure.repositories import ImportsRepository
from app.modules.imports.validators import validate_bank, validate_expenses, validate_invoices
from app.modules.imports.validators.products import validate_product

# --- helpers -----------------------------------------------------------------


def _to_uuid(v) -> UUID:
    return v if isinstance(v, UUID) else UUID(str(v))


def _idempotency_key(tenant_id: int | str, file_key: str | None, idx: int) -> str:
    base = f"{str(tenant_id)}:{file_key or ''}:{idx}"
    return hashlib.sha256(base.encode()).hexdigest()


def _validate_by_type(source_type: str, normalized: dict[str, Any]) -> list[dict[str, Any]]:
    # Feature flags simples vía env
    validate_currency = os.getenv("IMPORTS_VALIDATE_CURRENCY", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    # Activado por defecto: puede desactivarse con IMPORTS_REQUIRE_CATEGORIES=false
    require_categories = os.getenv("IMPORTS_REQUIRE_CATEGORIES", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    if source_type == "invoices":
        return validate_invoices(normalized, enable_currency_rule=validate_currency)
    if source_type in ("bank", "bank_transactions"):
        return validate_bank(normalized)
    if source_type in ("expenses", "receipts"):
        return validate_expenses(normalized, require_categories=require_categories)
    if source_type in ("products", "productos"):
        errs = validate_product(normalized)
        # Normalizar a formato {"field": str, "msg": str}
        out: list[dict[str, Any]] = []
        for e in errs:
            if isinstance(e, dict):
                out.append(e)
            else:
                out.append({"field": "product", "msg": str(e)})
        return out
    return []


def _normalize_dedupe_value(value: Any) -> str:
    """Canonicalize values used for dedupe hashes (dates, numbers, strings)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)):
        # Normalize numeric representation to avoid 100 vs 100.0 diffs
        try:
            return f"{float(value):.4f}".rstrip("0").rstrip(".")
        except Exception:
            return str(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        # Try a few common date formats to align 2024-02-01 vs 01/02/2024, etc.
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except Exception:
                continue
        # Lowercase to avoid case-only differences
        return s.lower()
    return str(value)


def _dedupe_hash(source_type: str, data: dict[str, Any], *, keys: list[str] | None = None) -> str:
    def g(*keys):
        for k in keys:
            if k in data and data[k] is not None:
                return _normalize_dedupe_value(data[k])
        return ""

    # If custom keys provided (from ImportMapping.dedupe_keys), honor them
    if keys:
        parts = [_normalize_dedupe_value(data.get(k)) for k in keys]
    elif source_type == "invoices":
        parts = [
            g("issuer_tax_id", "issuer", "supplier_tax_id"),
            g("invoice_number", "invoice", "number"),
            g("invoice_date", "date"),
            g("total_amount", "total"),
        ]
    elif source_type in ("bank", "bank_transactions"):
        parts = [
            g("statement_id"),
            g("entry_ref", "reference"),
            g("transaction_date", "date"),
            g("amount", "importe"),
            g("description", "concept", "concepto"),
        ]
    elif source_type in ("products", "productos"):
        parts = [g("name", "producto"), g("sku"), g("categoria", "category")]
    else:  # expenses/receipts
        parts = [
            g("expense_date", "date"),
            g("amount", "importe"),
            g("category", "categoria"),
            g("description", "concept", "concepto"),
        ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode()).hexdigest()


def _merge_src(raw: dict[str, Any] | None, normalized: dict[str, Any] | None) -> dict[str, Any]:
    """Devuelve raw sobreescrito por normalized cuando exista."""
    raw = raw or {}
    normalized = normalized or {}
    if not normalized:
        return raw
    merged = dict(raw)
    merged.update(normalized)
    return merged


def _parse_amount_value(v: Any) -> float | None:
    """Parses common OCR/Excel amount strings to float; tolerates currency symbols and thousands."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return float(v)
        except Exception:
            return None
    s = str(v).strip()
    if not s:
        return None
    # Remove currency/letters but keep signs, dots and commas
    s = re.sub(r"[^0-9,.\-]", "", s)
    if not s:
        return None
    # Determine decimal separator (use rightmost of . or ,)
    last_dot = s.rfind(".")
    last_comma = s.rfind(",")
    decimal_sep = "," if last_comma > last_dot else "."
    if decimal_sep == ",":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def _get_case_insensitive(raw: dict[str, Any], key: str) -> Any:
    """Returns value for key ignoring case differences."""
    for k, v in raw.items():
        try:
            if str(k).lower() == key.lower():
                return v
        except Exception:
            continue
    return None


def _normalize_bank_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort normalization for bank OCR rows when no mapping is provided."""
    if not isinstance(raw, dict):
        return None
    text_blob = " ".join(str(v) for v in raw.values() if v is not None)

    def _extract_date_from_text(text: str) -> str | None:
        m = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
        if m:
            return m.group(1)
        m = re.search(r"\b(\d{4}[/-]\d{2}[/-]\d{2})\b", text)
        if m:
            return m.group(1)
        return None

    tx_date = (
        raw.get("transaction_date")
        or raw.get("fecha")
        or raw.get("date")
        or raw.get("fecha_envio")
        or raw.get("fecha de envio")
        or raw.get("fecha de envío")
        or raw.get("fecha_valor")
        or raw.get("fecha valor")
        or raw.get("issue_date")
        or raw.get("value_date")
        or _get_case_insensitive(raw, "transaction_date")
        or _get_case_insensitive(raw, "fecha")
        or _get_case_insensitive(raw, "date")
        or _get_case_insensitive(raw, "fecha_envio")
        or _get_case_insensitive(raw, "fecha de envio")
        or _get_case_insensitive(raw, "fecha de envío")
        or _get_case_insensitive(raw, "fecha_valor")
        or _get_case_insensitive(raw, "fecha valor")
        or _get_case_insensitive(raw, "issue_date")
        or _get_case_insensitive(raw, "value_date")
        or _extract_date_from_text(text_blob)
    )
    amount = raw.get("amount") if raw.get("amount") is not None else raw.get("importe")
    if amount is None:
        amount = _get_case_insensitive(raw, "amount") or _get_case_insensitive(raw, "importe")
    parsed_amount = _parse_amount_value(amount)
    # As fallback, pick first numeric value in the row
    if parsed_amount is None:
        for v in raw.values():
            parsed_amount = _parse_amount_value(v)
            if parsed_amount is not None:
                break
    desc = (
        raw.get("description")
        or raw.get("descripcion")
        or raw.get("concepto")
        or raw.get("concept")
        or _get_case_insensitive(raw, "description")
        or _get_case_insensitive(raw, "descripcion")
        or _get_case_insensitive(raw, "concepto")
        or _get_case_insensitive(raw, "concept")
    )
    account = (
        raw.get("account")
        or raw.get("cuenta")
        or raw.get("iban")
        or _get_case_insensitive(raw, "account")
    )
    reference = (
        raw.get("entry_ref")
        or raw.get("reference")
        or raw.get("referencia")
        or raw.get("invoice")
        or _get_case_insensitive(raw, "entry_ref")
        or _get_case_insensitive(raw, "reference")
        or _get_case_insensitive(raw, "referencia")
    )

    normalized: dict[str, Any] = {}
    if tx_date:
        normalized["transaction_date"] = tx_date
    if parsed_amount is not None:
        normalized["amount"] = parsed_amount
    if desc:
        normalized["description"] = desc
    if account:
        normalized["account"] = account
    if reference:
        normalized["entry_ref"] = reference

    # Extra fallback: if no description, try joining non-empty text fields
    if not normalized.get("description"):
        texts = [str(v) for v in raw.values() if isinstance(v, str) and v.strip()]
        if texts:
            normalized["description"] = texts[0][:120]

    return normalized or None


def _normalize_invoice_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort normalization for invoice rows when no mapping is provided."""
    if not isinstance(raw, dict):
        return None

    invoice_number = (
        raw.get("num")
        or raw.get("invoice_number")
        or raw.get("invoice")
        or raw.get("number")
        or raw.get("numero")
        or raw.get("numero_factura")
        or raw.get("nro")
        or raw.get("folio")
        or _get_case_insensitive(raw, "invoice_number")
        or _get_case_insensitive(raw, "invoice")
        or _get_case_insensitive(raw, "number")
        or _get_case_insensitive(raw, "numero")
        or _get_case_insensitive(raw, "numero_factura")
        or _get_case_insensitive(raw, "nro")
        or _get_case_insensitive(raw, "folio")
    )
    invoice_date = (
        raw.get("invoice_date")
        or raw.get("issue_date")
        or raw.get("date")
        or raw.get("fecha")
        or _get_case_insensitive(raw, "invoice_date")
        or _get_case_insensitive(raw, "issue_date")
        or _get_case_insensitive(raw, "date")
        or _get_case_insensitive(raw, "fecha")
    )

    totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
    total_amount = _parse_amount_value(
        raw.get("total_amount") if raw.get("total_amount") is not None else raw.get("total")
    )
    if total_amount is None:
        total_amount = _parse_amount_value(raw.get("amount") or raw.get("importe"))
    if total_amount is None:
        total_amount = _parse_amount_value(
            totals.get("total") if isinstance(totals, dict) else None
        )

    net_amount = _parse_amount_value(raw.get("net_amount") or raw.get("subtotal"))
    if net_amount is None and isinstance(totals, dict):
        net_amount = _parse_amount_value(totals.get("subtotal"))
    tax_amount = _parse_amount_value(raw.get("tax_amount") or raw.get("tax") or raw.get("iva"))
    if tax_amount is None and isinstance(totals, dict):
        tax_amount = _parse_amount_value(totals.get("tax"))

    customer_name = (
        raw.get("customer_name")
        or raw.get("customer")
        or raw.get("cliente")
        or raw.get("buyer")
        or raw.get("vendor_name")
        or raw.get("vendor")
        or _get_case_insensitive(raw, "customer_name")
        or _get_case_insensitive(raw, "customer")
        or _get_case_insensitive(raw, "cliente")
        or _get_case_insensitive(raw, "buyer")
        or _get_case_insensitive(raw, "vendor_name")
        or _get_case_insensitive(raw, "vendor")
    )

    normalized: dict[str, Any] = {}
    if invoice_number:
        normalized["invoice_number"] = invoice_number
    if invoice_date:
        normalized["invoice_date"] = invoice_date
    if total_amount is not None:
        normalized["total_amount"] = total_amount
    if net_amount is not None:
        normalized["net_amount"] = net_amount
    if tax_amount is not None:
        normalized["tax_amount"] = tax_amount
    if customer_name:
        normalized["customer_name"] = customer_name

    if not normalized.get("invoice_number"):
        base = "|".join(
            [
                str(normalized.get("invoice_date") or ""),
                str(normalized.get("total_amount") or ""),
                str(normalized.get("customer_name") or ""),
            ]
        ).strip("|")
        if base:
            normalized["invoice_number"] = (
                "AUTO-" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:10].upper()
            )

    return normalized or None


def _normalize_expense_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort normalization for expenses/receipts when mapping is missing (OCR uploads)."""
    if not isinstance(raw, dict):
        return None
    exp_date = (
        raw.get("expense_date")
        or raw.get("fecha")
        or raw.get("date")
        or _get_case_insensitive(raw, "expense_date")
        or _get_case_insensitive(raw, "fecha")
        or _get_case_insensitive(raw, "date")
    )
    amount = raw.get("amount") if raw.get("amount") is not None else raw.get("importe")
    if amount is None:
        amount = _get_case_insensitive(raw, "amount") or _get_case_insensitive(raw, "importe")
    parsed_amount = _parse_amount_value(amount)
    # Fallback: scan any numeric field
    if parsed_amount is None:
        for v in raw.values():
            parsed_amount = _parse_amount_value(v)
            if parsed_amount is not None:
                break
    desc = (
        raw.get("description")
        or raw.get("descripcion")
        or raw.get("concepto")
        or raw.get("concept")
        or _get_case_insensitive(raw, "description")
        or _get_case_insensitive(raw, "descripcion")
        or _get_case_insensitive(raw, "concepto")
        or _get_case_insensitive(raw, "concept")
    )
    category = raw.get("category") or raw.get("categoria") or _get_case_insensitive(raw, "category")
    counterparty = (
        raw.get("cliente") or raw.get("customer") or _get_case_insensitive(raw, "cliente")
    )

    normalized: dict[str, Any] = {}
    if exp_date:
        normalized["expense_date"] = exp_date
    if parsed_amount is not None:
        normalized["amount"] = parsed_amount
    if desc:
        normalized["description"] = desc
    if category:
        normalized["category"] = category
    if counterparty:
        normalized["counterparty"] = counterparty

    return normalized or None


def _auto_normalize_row(source_type: str, raw: dict[str, Any]) -> dict[str, Any] | None:
    """Auto-mapping fallback for OCR/excel rows when no ImportMapping is provided."""
    if source_type in ("bank", "bank_transactions"):
        return _normalize_bank_row(raw)
    if source_type in ("invoices", "invoice"):
        return _normalize_invoice_row(raw)
    if source_type in ("expenses", "receipts"):
        return _normalize_expense_row(raw)
    return None


def _normalize_product_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Best-effort normalization for common product Excel headers when no mapping is provided.

    Maps frequent Spanish column names to canonical keys so validation/promote work
    even if the user didn’t configure an ImportMapping template.
    """
    if not isinstance(raw, dict):
        return {}
    # Work on lowercase keys for flexible matching
    lower = {str(k).strip().lower(): v for k, v in raw.items()}

    out: dict[str, Any] = {}
    # Name
    out["name"] = (
        lower.get("name")
        or lower.get("producto")
        or lower.get("nombre")
        or lower.get("articulo")
        or raw.get("PRODUCTO")
        or raw.get("NOMBRE")
        or raw.get("ARTICULO")
        or ""
    )
    # Price (map to canonical "price")
    out_price = (
        lower.get("precio")
        or lower.get("price")
        or lower.get("pvp")
        or lower.get("precio unitario")
        or lower.get("precio unitario venta")
        or raw.get("PRECIO UNITARIO VENTA")
        or raw.get("PRECIO")
    )
    try:
        out["price"] = (
            float(str(out_price).replace(",", ".")) if out_price not in (None, "") else None
        )
    except Exception:
        out["price"] = out_price

    cost_val = (
        lower.get("costo")
        or lower.get("cost")
        or lower.get("coste")
        or lower.get("costo promedio")
        or lower.get("costo unitario")
        or lower.get("cost_price")
        or lower.get("unit_cost")
        or raw.get("COSTO")
        or raw.get("COSTO PROMEDIO")
    )
    parsed_cost = _parse_amount_value(cost_val)
    if parsed_cost is not None:
        out["cost_price"] = parsed_cost
        out["cost"] = parsed_cost
        out["unit_cost"] = parsed_cost

    # Quantity / stock (prefer sobrante diario or cantidad)
    stock_val = (
        lower.get("sobrante diario")
        or lower.get("cantidad")
        or lower.get("quantity")
        or lower.get("stock")
        or lower.get("existencia")
        or lower.get("existencias")
        or lower.get("unidades")
        or raw.get("CANTIDAD")
        or raw.get("EXISTENCIA")
        or raw.get("EXISTENCIAS")
        or raw.get("UNIDADES")
    )
    try:
        out["stock"] = (
            float(str(stock_val).replace(",", ".")) if stock_val not in (None, "") else None
        )
    except Exception:
        out["stock"] = stock_val

    # Category
    out["categoria"] = lower.get("categoria") or lower.get("category") or raw.get("CATEGORIA") or ""
    # SKU/code (only set if present and non-empty)
    sku_val = (
        lower.get("sku")
        or lower.get("codigo")
        or lower.get("c?digo")
        or lower.get("code")
        or raw.get("CODIGO")
        or raw.get("C?DIGO")
    )
    if sku_val not in (None, "", "-"):
        out["sku"] = sku_val
    # Unit
    out["unit"] = (
        lower.get("unit") or lower.get("unidad") or lower.get("uom") or raw.get("UNIDAD") or "unit"
    )
    return out


# --- use cases ---------------------------------------------------------------


def _create_batch_impl(
    db: Session, tenant_id: int, user_id: Any, dto: dict[str, Any]
) -> ImportBatch:
    # created_by se guarda como String (UUID en string si es posible)
    try:
        created_by_uuid = user_id if isinstance(user_id, UUID) else _to_uuid(user_id)
        created_by = str(created_by_uuid)
    except Exception:
        created_by = str(uuid4())

    batch = ImportBatch(
        tenant_id=tenant_id,  # <-- INT (como en tus modelos)
        source_type=dto["source_type"],
        origin=dto.get("origin") or "api",
        file_key=dto.get("file_key"),
        mapping_id=dto.get("mapping_id"),  # esto es UUID o None según tu modelo
        status="PENDING",
        created_by=created_by,  # columna String
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def create_batch(
    db: Session,
    tenant_id: int,
    *args: Any,
    **kwargs: Any,
) -> ImportBatch:
    """
    Wrapper que soporta la API moderna (user_id + dto) y la firma legacy usada en los tests.
    """
    if len(args) == 2 and isinstance(args[1], dict):
        user_id, dto = args
        return _create_batch_impl(db, tenant_id, user_id, dto)

    user_id = kwargs.get("user_id") or kwargs.get("created_by") or uuid4()
    dto = dict(kwargs.get("dto") or {})
    legacy_source = kwargs.get("source_type")
    if legacy_source:
        dto.setdefault("source_type", legacy_source)
    legacy_description = kwargs.get("description")
    if legacy_description:
        dto.setdefault("description", legacy_description)
    dto.setdefault("origin", kwargs.get("origin") or dto.get("origin"))
    dto.setdefault("file_key", kwargs.get("file_key") or dto.get("file_key"))
    dto.setdefault("mapping_id", kwargs.get("mapping_id") or dto.get("mapping_id"))

    if "source_type" not in dto:
        raise ValueError("source_type is required to create import batch")

    return _create_batch_impl(db, tenant_id, user_id, dto)


def _build_mock_normalized(source_type: str, suffix: str | None = None) -> dict[str, Any]:
    """Construye datos mock para las pruebas heredadas."""
    today = datetime.utcnow().date().isoformat()
    identifier = suffix or "legacy"

    if source_type in ("invoices",):
        return {
            "proveedor": {"tax_id": "1790016919001", "nombre": "Proveedor Legacy"},
            "invoice_number": f"INV-{identifier}",
            "invoice_date": today,
            "subtotal": 100.0,
            "tax": 12.0,
            "total": 112.0,
            "lines": [
                {
                    "descripcion": "Item legacy",
                    "cantidad": 1,
                    "precio_unitario": 112.0,
                    "iva": 12.0,
                }
            ],
        }

    if source_type in ("expenses", "receipts"):
        return {
            "description": f"Gasto legacy {identifier}",
            "expense_date": today,
            "category": "otros",
            "total": 45.0,
            "tax": 0.0,
            "amount": 45.0,
        }

    return {
        "description": f"Documento legacy {identifier}",
        "date": today,
        "amount": 123.45,
    }


def ingest_file(
    db: Session,
    tenant_id: int | str,
    batch_id: UUID | str,
    *,
    file_key: str,
    filename: str,
    file_size: int,
    file_sha256: str,
) -> ImportItem:
    batch_uuid = _to_uuid(batch_id)
    tenant_uuid = _to_uuid(tenant_id)
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_uuid).first()
    if not batch:
        raise ValueError("Batch no encontrado")
    if not batch.file_sha256:
        batch.file_sha256 = file_sha256
        db.add(batch)
        db.flush()

    existing_count = (
        db.query(func.count(ImportItem.id)).filter(ImportItem.batch_id == batch_uuid).scalar() or 0
    )
    idx = int(existing_count)
    item = ImportItem(
        tenant_id=batch.tenant_id or tenant_uuid,
        batch_id=batch.id,
        idx=idx,
        raw={
            "filename": filename,
            "file_key": file_key,
            "file_size": file_size,
            "file_sha256": file_sha256,
        },
        normalized=None,
        canonical_doc=None,
        status="preprocessing",
        errors=[],
        dedupe_hash=file_sha256,
        idempotency_key=_idempotency_key(tenant_uuid, file_key, idx),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def extract_item_sync(
    db: Session,
    tenant_id: int | str,
    item_id: UUID | str,
) -> ImportItem:
    item_uuid = _to_uuid(item_id)
    item = db.query(ImportItem).filter(ImportItem.id == item_uuid).first()
    if not item:
        raise ValueError("Item no encontrado")

    batch = item.batch or db.query(ImportBatch).filter(ImportBatch.id == item.batch_id).first()
    normalized = _build_mock_normalized(batch.source_type, suffix=str(item.idx))
    item.normalized = normalized
    item.status = "extracted"
    item.errors = []
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def validate_item_sync(
    db: Session,
    tenant_id: int | str,
    item_id: UUID | str,
) -> ImportItem:
    item_uuid = _to_uuid(item_id)
    item = db.query(ImportItem).filter(ImportItem.id == item_uuid).first()
    if not item:
        raise ValueError("Item no encontrado")

    batch = item.batch or db.query(ImportBatch).filter(ImportBatch.id == item.batch_id).first()
    errors = _validate_by_type(batch.source_type, item.normalized or {})
    item.errors = errors
    if errors:
        item.status = "validation_failed"
    else:
        item.status = "validated"
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def ingest_rows(
    db: Session,
    tenant_id: int,
    batch: ImportBatch,
    rows: Iterable[dict[str, Any]],
    mappings: dict[str, Any] | None = None,
    transforms: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
    dedupe_keys: list[str] | None = None,
):
    t0 = datetime.utcnow()
    rows_list = list(rows)
    # batch.tenant_id is already UUID, use directly
    tenant_id = batch.tenant_id
    # Debug logging (emoji removed to avoid console encoding issues)
    # print(f"DEBUG ingest_rows: batch_id={batch.id}, rows count={len(rows_list)}, tenant_id={tenant_id}")

    repo = ImportsRepository()
    created: list[dict[str, Any]] = []
    ir_builder = IRBuilder()

    tpl_v2: TemplateV2 | None = None
    # Si mappings es {} o None, considerar auto-match
    if isinstance(mappings, dict) and not mappings:
        mappings = None

    # Siempre intentar auto-selección de TemplateV2, aun si hay mapping legacy
    try:
        q = db.query(ImportMapping).filter(ImportMapping.tenant_id == batch.tenant_id)
        if batch.source_type not in ("generic", "unknown", "", None):
            q = q.filter(ImportMapping.source_type == batch.source_type)
        candidates = q.order_by(ImportMapping.created_at.desc()).all()
        tpl_pairs: list[TemplateV2] = []
        for tpl in candidates:
            if isinstance(tpl.mappings, dict) and tpl.mappings.get("template_version") == 2:
                try:
                    tv2 = TemplateV2(**tpl.mappings)
                    tpl_pairs.append(tv2)
                    if tpl.id == batch.mapping_id:
                        tpl_v2 = tv2
                except Exception:
                    continue
        if tpl_v2 is None and tpl_pairs:
            filename = (
                getattr(batch, "original_filename", None) or getattr(batch, "origin", "") or ""
            )
            matcher = TemplateMatcher(tpl_pairs)
            matched = matcher.match(filename, "es")
            if matched:
                tpl_v2 = matched
    except Exception:
        tpl_v2 = None

    if mappings and isinstance(mappings, dict) and mappings.get("template_version") == 2:
        errs = validate_template(mappings)
        if errs:
            raise ValueError(f"TemplateV2 inválido: {errs}")
        tpl_v2 = TemplateV2(**mappings)
        dedupe_keys = tpl_v2.dedupe_keys or dedupe_keys
        transforms = transforms or tpl_v2.transforms
        defaults = defaults or tpl_v2.defaults
    elif tpl_v2:
        dedupe_keys = tpl_v2.dedupe_keys or dedupe_keys
        transforms = transforms or tpl_v2.transforms
        defaults = defaults or tpl_v2.defaults
    for idx, raw in enumerate(rows_list):
        # Desempaquetar payloads que traen los datos en la clave "datos" manteniendo meta como fallback
        raw_effective = raw
        if isinstance(raw, dict) and "datos" in raw and isinstance(raw.get("datos"), dict):
            # Copia los datos reales y conserva metadatos (tipo/origen) si no pisan claves
            base = dict(raw.get("datos") or {})
            for k, v in raw.items():
                if k != "datos" and k not in base:
                    base[k] = v
            raw_effective = base

        normalized = None

        ir_rows = ir_builder.build_from_rows([raw_effective], origin="api")
        raw_ir = ir_rows[0] if ir_rows else raw_effective

        if tpl_v2:
            interpreter = TemplateInterpreter(tpl_v2)
            language = raw_ir.get("language", "es") if isinstance(raw_ir, dict) else "es"
            headers_raw = list(raw_effective.keys())
            try:
                headers_norm = normalize_headers(headers_raw, tpl_v2.header_normalization, language)
            except Exception:
                headers_norm = [str(h).strip().lower() for h in headers_raw]
            normalized_row = {
                h_norm: raw_effective.get(h_raw) for h_norm, h_raw in zip(headers_norm, headers_raw)
            }
            processed = interpreter.process_rows([normalized_row])
            if processed:
                normalized = processed[0] if len(processed) == 1 else processed
        else:
            # Legacy mappings eliminados: usamos solo heurÃ­sticas automÃ¡ticas
            if batch.source_type in ("products", "productos"):
                normalized = _normalize_product_row(raw_effective)
            if not normalized:
                auto_norm = _auto_normalize_row(batch.source_type, raw_effective)
                if auto_norm:
                    normalized = auto_norm

        src = _merge_src(raw_effective, normalized)
        errors = _validate_by_type(batch.source_type, src)
        status = ImportItemStatus.OK if not errors else ImportItemStatus.ERROR_VALIDATION
        dedupe = _dedupe_hash(batch.source_type, src, keys=dedupe_keys)
        idem = _idempotency_key(tenant_id, f"{batch.id}:{batch.file_key or ''}", idx)
        created.append(
            {
                "idx": idx,
                "raw": raw_ir,
                "normalized": normalized,
                "status": status,
                "errors": errors,
                "idempotency_key": idem,
                "dedupe_hash": dedupe,
            }
        )
    # Debug logging
    # print(f"DEBUG: created items count={len(created)}")
    if created:
        # print(f"DEBUG: Calling bulk_add_items with {len(created)} items")
        repo.bulk_add_items(db, tenant_id, batch.id, created)  # tenant_id UUID
        # Ajustar estado del batch según validaciones iniciales
        total = len(created)
        oks = sum(1 for it in created if it.get("status") == ImportItemStatus.OK)
        errs = sum(
            1
            for it in created
            if it.get("status")
            in (ImportItemStatus.ERROR_VALIDATION, ImportItemStatus.ERROR_PROMOTION, "ERROR")
        )
        if total == 0:
            batch.status = ImportBatchStatus.PENDING
        elif errs == 0 and oks == total:
            batch.status = ImportBatchStatus.READY
        elif oks > 0 and errs > 0:
            batch.status = ImportBatchStatus.PARTIAL
        else:
            batch.status = ImportBatchStatus.ERROR
        db.add(batch)
        db.commit()
        db.refresh(batch)
        # print(f"DEBUG: Items committed, batch status={batch.status}")
    else:
        # Si el parser no produjo items, marca el lote como vacío para evitar mostrarlo como listo
        batch.status = ImportBatchStatus.EMPTY
        db.add(batch)
        db.commit()
        db.refresh(batch)
    t1 = datetime.utcnow()
    try:
        logging.getLogger("imports").info(
            "ingest_rows",
            extra={
                "tenant": tenant_id,
                "batch_id": str(batch.id),
                "items_total": len(created),
                "t_parse_ms": int((t1 - t0).total_seconds() * 1000),
            },
        )
    except Exception:
        pass
    return repo.list_items(db, tenant_id, batch.id)


def revalidate_batch(db: Session, tenant_id: int, batch_id: UUID | str):
    batch_uuid = _to_uuid(batch_id)
    repo = ImportsRepository()
    batch = repo.get_batch(db, tenant_id, batch_uuid)  # tenant_id UUID, batch_id UUID
    if not batch:
        return []
    items = repo.list_items(db, tenant_id, batch_uuid)
    for it in items:
        src = _merge_src(it.raw, it.normalized)
        errors = _validate_by_type(batch.source_type, src)
        it.errors = errors
        it.status = ImportItemStatus.OK if not errors else ImportItemStatus.ERROR_VALIDATION
        db.add(it)
    db.commit()
    out = repo.list_items(db, tenant_id, batch_uuid)
    # Update batch status: VALIDATED if all OK, PARTIAL if mixed, READY if no items
    total = len(out)
    oks = sum(1 for x in out if x.status == ImportItemStatus.OK)
    errs = sum(1 for x in out if x.status == ImportItemStatus.ERROR_VALIDATION)
    if total > 0:
        if errs == 0 and oks == total:
            batch.status = ImportBatchStatus.VALIDATED
        elif oks > 0 and errs > 0:
            batch.status = ImportBatchStatus.PARTIAL
        else:
            batch.status = ImportBatchStatus.ERROR
        db.add(batch)
        db.commit()
    try:
        logging.getLogger("imports").info(
            "revalidate_batch",
            extra={
                "tenant": tenant_id,
                "batch_id": str(batch_uuid),
                "items_total": len(out),
                "items_ok": sum(1 for x in out if x.status == "OK"),
                "items_error": sum(1 for x in out if x.status and x.status.startswith("ERROR")),
            },
        )
    except Exception:
        pass
    return out


def patch_item(
    db: Session, tenant_id: int, user_id: Any, batch_id, item_id, field: str, value: Any
):
    batch_uuid = _to_uuid(batch_id)
    item_uuid = _to_uuid(item_id)

    repo = ImportsRepository()
    batch = repo.get_batch(db, tenant_id, batch_uuid)
    if not batch:
        return None

    from sqlalchemy import and_

    it = (
        db.query(ImportItem)
        .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
        .filter(and_(ImportItem.id == item_uuid, ImportBatch.tenant_id == tenant_id))
        .first()
    )
    if not it:
        return None

    # 👇 CLAVE: partir de todos los campos disponibles
    base = it.normalized or it.raw or {}
    normalized = dict(base)
    old_value = normalized.get(field)
    normalized[field] = value
    it.normalized = normalized

    # revalidar con el payload completo ya actualizado
    src = _merge_src(it.raw, it.normalized)
    errors = _validate_by_type(batch.source_type, src)
    it.errors = errors
    it.status = "OK" if not errors else "ERROR_VALIDATION"
    db.add(it)

    # corrección (user_id → UUID si puedes; si no, genera uno)
    try:
        uid = user_id if isinstance(user_id, UUID) else _to_uuid(user_id)
    except Exception:
        uid = uuid4()

    corr = ImportItemCorrection(
        tenant_id=tenant_id,
        item_id=item_uuid,
        user_id=uid,
        field=field,
        old_value=old_value,
        new_value=value,
    )
    db.add(corr)
    db.commit()
    db.refresh(it)
    return it


def promote_batch(db: Session, tenant_id: int, batch_id, *, options: dict | None = None):
    batch_uuid = _to_uuid(batch_id)
    tenant_uuid = _to_uuid(tenant_id)

    repo = ImportsRepository()
    batch = repo.get_batch(db, tenant_uuid, batch_uuid)
    if not batch:
        return {"created": 0, "skipped": 0, "failed": 0}

    # Consider all items; we'll count already promoted as skipped to make idempotency visible
    items = repo.list_items(db, tenant_uuid, batch_uuid)
    created = skipped = failed = 0
    # User-chosen destination overrides the auto-detected source_type.
    user_destination = (options or {}).get("destination")

    # Special handling for recipes: we handle them differently
    if batch.source_type == "recipes" and not user_destination:
        handler = RecipeHandler
    elif user_destination:
        handler = {
            "invoices": InvoiceHandler,
            "expenses": ExpenseHandler,
            "sales": InvoiceHandler,
            "bank": BankHandler,
        }.get(user_destination, InvoiceHandler)
    else:
        handler = {
            "invoices": InvoiceHandler,
            "bank": BankHandler,
            "receipts": InvoiceHandler,
            "expenses": ExpenseHandler,
            "products": ProductHandler,
            "productos": ProductHandler,
        }.get(batch.source_type, InvoiceHandler)

    t0 = datetime.utcnow()
    promoted_hashes: set[str] = set()
    collect_promoted = bool(options and options.get("collect_promoted"))
    promoted_items: list[dict[str, Any]] = []
    for it in items:
        # Already promoted: count as skipped (idempotent).
        # Guard against stale states from past bugs: PROMOTED but promoted_id is NULL.
        # In that case, retry promotion instead of skipping, otherwise UI says "PROMOTED"
        # but nothing exists in the destination module.
        if it.status == ImportItemStatus.PROMOTED:
            if getattr(it, "promoted_id", None):
                skipped += 1
                continue
            # Retry: downgrade to OK so this item can be promoted again.
            it.status = ImportItemStatus.OK
            it.errors = (it.errors or []) + [
                {
                    "phase": "promotion",
                    "message": "Stale PROMOTED state without promoted_id; retrying promotion",
                }
            ]
            db.add(it)
        # Only attempt to promote valid items
        if it.status != ImportItemStatus.OK:
            continue
        try:
            if it.dedupe_hash and (
                repo.exists_promoted_hash(db, tenant_uuid, it.dedupe_hash)
                or it.dedupe_hash in promoted_hashes
            ):
                # Log duplicate as an incident so it’s visible in the panel
                try:
                    db.add(
                        Incident(
                            tenant_id=tenant_uuid,
                            tipo="warning",
                            severidad="low",
                            titulo="Elemento duplicado en importación",
                            descripcion="Se omitió la promoción de un ítem por hash duplicado",
                            context={
                                "batch_id": str(batch_uuid),
                                "item_id": str(it.id),
                                "idx": it.idx,
                                "source_type": batch.source_type,
                                "dedupe_hash": it.dedupe_hash,
                            },
                            auto_detected=True,
                        )
                    )
                    db.flush()
                except Exception:
                    pass
                skipped += 1
                continue

            # Todos los handlers ahora usan la firma completa con db y tenant_id
            res = handler.promote(
                db,
                tenant_uuid,
                it.normalized or it.raw or {},
                it.promoted_id,
                options=options or {},
            )

            if res.skipped:
                if getattr(res, "domain_id", None):
                    it.promoted_to = user_destination or batch.source_type
                    it.promoted_id = _to_uuid(res.domain_id)
                    it.promoted_at = datetime.utcnow()
                    it.status = ImportItemStatus.PROMOTED
                    db.add(it)
                skipped += 1
                continue
            # Defensive: some handlers were returning domain_id=None on errors. That must not
            # mark the item as PROMOTED, otherwise UI shows PROMOTED but nothing is created.
            if not getattr(res, "domain_id", None):
                it.status = ImportItemStatus.ERROR_PROMOTION
                it.errors = (it.errors or []) + [
                    {
                        "phase": "promotion",
                        "message": "Handler did not return a destination id (domain_id=None)",
                        "source_type": batch.source_type,
                    }
                ]
                db.add(it)
                failed += 1
                continue
            # promoted_to indica el módulo/tabla destino real
            it.promoted_to = user_destination or batch.source_type
            it.promoted_id = _to_uuid(res.domain_id) if res.domain_id else None
            it.promoted_at = datetime.utcnow()
            it.status = ImportItemStatus.PROMOTED
            db.add(it)
            if it.dedupe_hash:
                promoted_hashes.add(it.dedupe_hash)

            lineage = ImportLineage(
                tenant_id=tenant_uuid,
                item_id=it.id,  # UUID
                promoted_to=it.promoted_to,
                promoted_ref=res.domain_id or "",
            )
            db.add(lineage)
            created += 1
            if collect_promoted:
                promoted_items.append(
                    {
                        "item_id": str(it.id),
                        "promoted_id": str(res.domain_id) if res.domain_id else None,
                        "src": _merge_src(it.raw, it.normalized),
                    }
                )
        except Exception as exc:
            # If session is in pending rollback state, rollback first before making changes
            if db.is_active:
                try:
                    db.rollback()
                except Exception:
                    pass
            it.status = ImportItemStatus.ERROR_PROMOTION
            it.errors = (it.errors or []) + [
                {"phase": "promotion", "message": str(exc) or "Unhandled error"}
            ]
            db.add(it)
            failed += 1

    # Batch-level status after promotion attempt.
    promotable_total = sum(
        1 for it in items if it.status in (ImportItemStatus.OK, ImportItemStatus.PROMOTED)
    )
    if failed > 0:
        batch.status = (
            ImportBatchStatus.PARTIAL if (created + skipped) > 0 else ImportBatchStatus.ERROR
        )
    else:
        if promotable_total > 0 and (created + skipped) > 0:
            batch.status = ImportBatchStatus.PROMOTED
        elif created == 0 and skipped == 0:
            # Nothing promoted and nothing skipped: keep ready state (e.g. all non-OK items)
            batch.status = ImportBatchStatus.READY
        else:
            batch.status = ImportBatchStatus.PROMOTED
    db.add(batch)

    # Flush pending changes to catch any remaining errors before final commit
    try:
        db.flush()
    except Exception:
        db.rollback()
        raise

    db.commit()
    t1 = datetime.utcnow()
    try:
        logging.getLogger("imports").info(
            "promote_batch",
            extra={
                "tenant": tenant_id,
                "tenant_uuid": str(tenant_uuid),
                "batch_id": str(batch_uuid),
                "items_total": len(items),
                "items_ok": created,
                "items_error": failed,
                "t_promote_ms": int((t1 - t0).total_seconds() * 1000),
            },
        )
    except Exception:
        pass
    result = {"created": created, "skipped": skipped, "failed": failed}
    if collect_promoted:
        result["promoted_items"] = promoted_items
    return result


def _detectar_tipo_por_texto(txt: str) -> str:
    t = txt.lower()
    # Detectar tickets POS primero (más específico)
    if "ticket de venta" in t or "ticket venta" in t or "gracias por su compra" in t:
        return "ticket_pos"
    if re.search(r"n[ºo°]?\s*r[-\s]*\d+", t):
        return "ticket_pos"
    if re.search(r"\d+[.,]?\d*\s*x\s+.+\s*[-–]\s*\$?\s*\d", t):
        return "ticket_pos"
    if "iban" in t or "saldo" in t or "transferencia" in t:
        return "bank"
    # Priorizar recibos/recibos de pago antes que facturas
    if "receipt" in t or "recibo" in t or "paid" in t:
        return "expenses"
    if "factura" in t or "n° factura" in t or "invoice" in t:
        return "invoices"
    return "receipts"


def ingest_photo(
    db: Session, tenant_id: str, user_id: str, batch: ImportBatch, file: UploadFile
) -> ImportItem:
    # 1) leer bytes y normalizar orientación
    content = file.file.read()
    content = exif_auto_orienta(content)

    # 2) guardar adjunto (devuelve file_key y sha256)
    file_key, sha256 = guardar_adjunto_bytes(
        tenant_id, content, filename=file.filename or "foto.jpg"
    )

    # 3) OCR
    texto = ocr_texto(content, filename=file.filename or "")  # devuelve str

    # 4) detectar tipo y extraer campos
    tipo = _detectar_tipo_por_texto(texto)
    if tipo == "invoices":
        raw = parse_texto_factura(texto)
    elif tipo == "bank":
        raw = parse_texto_banco(texto)
    elif tipo == "ticket_pos":
        from app.modules.imports.extractores.extractor_ticket import extraer_ticket

        resultados = extraer_ticket(texto)
        if resultados:
            canonical = resultados[0]
            totals = canonical.get("totals", {})
            raw = {
                "tipo": "ticket_pos",
                "importe": totals.get("total", 0.0),
                "fecha": canonical.get("issue_date"),
                "invoice": canonical.get("invoice_number"),
                "concepto": "Ticket de venta POS",
                "categoria": "ventas",
                "origen": "ocr",
            }
        else:
            raw = parse_texto_recibo(texto)
    else:
        raw = parse_texto_recibo(texto)

    # 5) mapping/template
    normalized = None
    tpl_v2: TemplateV2 | None = None
    try:
        if batch.mapping_id:
            mp = db.query(ImportMapping).filter(ImportMapping.id == batch.mapping_id).first()
            if mp:
                if isinstance(mp.mappings, dict) and mp.mappings.get("template_version") == 2:
                    errs = validate_template(mp.mappings)
                    if not errs:
                        tpl_v2 = TemplateV2(**mp.mappings)
        if tpl_v2 is None:
            qtpl = db.query(ImportMapping).filter(ImportMapping.tenant_id == batch.tenant_id)
            if getattr(batch, "source_type", None) not in ("generic", "unknown", "", None):
                qtpl = qtpl.filter(ImportMapping.source_type == batch.source_type)
            tpls = qtpl.order_by(ImportMapping.created_at.desc()).all()
            tv2_list: list[TemplateV2] = []
            for t in tpls:
                if isinstance(t.mappings, dict) and t.mappings.get("template_version") == 2:
                    try:
                        tv2 = TemplateV2(**t.mappings)
                        tv2_list.append(tv2)
                    except Exception:
                        continue
            if tv2_list:
                matcher = TemplateMatcher(tv2_list)
                filename = (
                    getattr(batch, "original_filename", None) or getattr(batch, "origin", "") or ""
                )
                matched = matcher.match(filename, "es")
                if matched:
                    tpl_v2 = matched
    except Exception:
        tpl_v2 = None

    if tpl_v2:
        interpreter = TemplateInterpreter(tpl_v2)
        headers_raw = list(raw.keys()) if isinstance(raw, dict) else []
        lang = "es"
        try:
            headers_norm = normalize_headers(headers_raw, tpl_v2.header_normalization, lang)
        except Exception:
            headers_norm = headers_raw
        normalized_row = {
            h_norm: raw.get(h_raw) for h_norm, h_raw in zip(headers_norm, headers_raw)
        }
        processed = interpreter.process_rows([normalized_row])
        if processed:
            normalized = processed[0] if len(processed) == 1 else processed
    else:
        # Legacy mappings eliminados: usar solo auto-normalizaciÃ³n heurÃ­stica por tipo
        normalized = _auto_normalize_row(batch.source_type or tipo, raw)

    ir = IRBuilder().build_from_ocr(texto, sha256, ocr_job_id="", page_no=1, attachment_ids=[])

    # 6) crear item + adjunto
    idx = (db.query(ImportItem).filter(ImportItem.batch_id == batch.id).count() or 0) + 1
    item = ImportItem(
        batch_id=batch.id,
        idx=idx,
        raw=ir,
        normalized=normalized,
        idempotency_key=_idempotency_key(tenant_id, batch.file_key or file_key, idx),
    )
    src = _merge_src(item.raw, item.normalized)
    errors = _validate_by_type(batch.source_type, src)
    item.errors = errors
    item.status = "OK" if not errors else "ERROR_VALIDATION"
    db.add(item)
    db.flush()

    att = ImportAttachment(
        item_id=item.id,
        file_key=file_key,
        kind="photo",
        sha256=sha256,
        ocr_text=texto,
        page_no=1,
    )
    db.add(att)
    try:
        ir["artifacts_ref"]["attachment_ids"] = [str(att.id)]
        item.raw = ir
    except Exception:
        pass
    db.commit()
    db.refresh(item)
    return item


def attach_photo_and_reocr(
    db: Session, tenant_id: str, user_id: str, item: ImportItem, file: UploadFile
) -> ImportItem:
    content = file.file.read()
    content = exif_auto_orienta(content)
    file_key, sha256 = guardar_adjunto_bytes(
        tenant_id, content, filename=file.filename or "foto.jpg"
    )
    texto = ocr_texto(content, filename=file.filename or "")

    # Re-extraer valores "inteligentes" (NO pisa raw original; añade sugerencias)
    tipo = item.batch.source_type or _detectar_tipo_por_texto(texto)
    if tipo == "invoices":
        suger = parse_texto_factura(texto)
    elif tipo == "bank":
        suger = parse_texto_banco(texto)
    elif tipo == "ticket_pos":
        from app.modules.imports.extractores.extractor_ticket import extraer_ticket

        resultados = extraer_ticket(texto)
        if resultados:
            canonical = resultados[0]
            totals = canonical.get("totals", {})
            suger = {
                "tipo": "ticket_pos",
                "importe": totals.get("total", 0.0),
                "fecha": canonical.get("issue_date"),
                "invoice": canonical.get("invoice_number"),
                "concepto": "Ticket de venta POS",
                "categoria": "ventas",
            }
        else:
            suger = parse_texto_recibo(texto)
    else:
        suger = parse_texto_recibo(texto)

    # **No sobrescribas**: aplica sugerencias como parches si los campos están vacíos
    norm = dict(item.normalized or {})
    for k, v in suger.items():
        if k not in norm or norm[k] in (None, "", 0):
            norm[k] = v
    item.normalized = norm
    src = _merge_src(item.raw, item.normalized)
    errors = _validate_by_type(
        item.batch.source_type if hasattr(item, "batch") else "receipts", src
    )
    item.errors = errors
    item.status = "OK" if not errors else "ERROR_VALIDATION"

    att = ImportAttachment(
        item_id=item.id,
        file_key=file_key,
        kind="photo",
        sha256=sha256,
        ocr_text=texto,
        page_no=1,
    )
    db.add(att)
    try:
        raw_ir = item.raw or {}
        if isinstance(raw_ir, dict):
            artifacts = raw_ir.get("artifacts_ref") or {}
            attachment_ids = artifacts.get("attachment_ids") or []
            attachment_ids.append(str(att.id))
            artifacts["attachment_ids"] = attachment_ids
            raw_ir["artifacts_ref"] = artifacts
            item.raw = raw_ir
    except Exception:
        pass
    db.commit()
    db.refresh(item)
    return item
