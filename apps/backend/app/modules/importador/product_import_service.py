from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.inventory.stock import StockItem
from app.models.inventory.warehouse import Warehouse
from app.modules.products.interface.http.tenant import (
    _generate_next_sku,
    _normalize_category_name,
    _resolve_category_id,
)

SUMMARY_NAMES = {
    "total",
    "subtotal",
    "resumen",
    "sum",
    "totales",
}

NAME_KEYWORDS = (
    "producto",
    "nombre",
    "descripcion",
    "description",
    "item",
    "articulo",
    "product",
    "name",
    "denominacion",
)
PRICE_KEYWORDS = (
    "precio unitario",
    "unit price",
    "precio venta",
    "sale price",
    "pvp",
    "price",
    "precio",
    "valor",
)
PRICE_REJECT_KEYWORDS = ("total", "importe total", "subtotal")
COST_KEYWORDS = ("costo", "cost", "compra", "purchase")
SKU_KEYWORDS = ("sku", "codigo", "code", "ean", "barcode", "referencia", "ref")
CATEGORY_KEYWORDS = ("categoria", "category", "familia", "grupo", "linea")
DESCRIPTION_KEYWORDS = ("descripcion", "description", "detalle", "detalle producto")
EXPLICIT_STOCK_KEYWORDS = (
    "stock",
    "existencia",
    "disponible",
    "inventario",
    "saldo",
    "cantidad stock",
)
AMBIGUOUS_STOCK_KEYWORDS = ("cantidad", "qty", "quantity", "unidades", "units")
OPERATIONAL_KEYWORDS = (
    "venta",
    "diaria",
    "sobrante",
    "produc",
    "consumo",
    "merma",
)
SHEET_HINT_KEYWORDS = (
    "product",
    "producto",
    "productos",
    "catalog",
    "catalogo",
    "inventory",
    "inventario",
    "stock",
    "price list",
    "lista precios",
)


@dataclass
class ProductCandidate:
    row_index: int
    name: str
    price: float | None
    stock: float | None
    unit: str
    sku: str | None = None
    category_name: str | None = None
    description: str | None = None
    cost_price: float | None = None
    tax_rate: float | None = None
    product_metadata: dict[str, Any] | None = None


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if numeric == numeric else None

    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("\xa0", " ")
    raw = re.sub(r"[^0-9,.\-]", "", raw)
    if not raw or raw in {"-", ".", ","}:
        return None

    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")

    try:
        return float(raw)
    except ValueError:
        return None


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for raw_key, value in row.items():
        key = _norm(raw_key)
        if not key or key.startswith("sheet"):
            continue
        if key not in normalized:
            normalized[key] = value
    return normalized


def _select_document_rows(
    datos: dict[str, Any], sheet_name: str | None = None
) -> tuple[list[dict[str, Any]], str | None]:
    rows_by_sheet = datos.get("filas_por_hoja", {})
    if isinstance(rows_by_sheet, dict) and rows_by_sheet:
        if sheet_name and isinstance(rows_by_sheet.get(sheet_name), list):
            return rows_by_sheet.get(sheet_name) or [], sheet_name

        active_sheet = datos.get("sheet_usada")
        if active_sheet in rows_by_sheet and isinstance(rows_by_sheet.get(active_sheet), list):
            return rows_by_sheet.get(active_sheet) or [], str(active_sheet)

        for current_sheet, rows in rows_by_sheet.items():
            if isinstance(rows, list):
                return rows, str(current_sheet)

    rows = datos.get("filas", [])
    if isinstance(rows, list):
        return rows, sheet_name

    return [], sheet_name


def _pick_key(
    keys: list[str],
    keywords: tuple[str, ...],
    reject_keywords: tuple[str, ...] = (),
) -> str | None:
    best_key: str | None = None
    best_score = 0

    for key in keys:
        score = 0
        for keyword in keywords:
            if key == keyword:
                score += 10
            elif keyword in key:
                score += 4
        for reject in reject_keywords:
            if reject in key:
                score -= 5
        if score > best_score:
            best_score = score
            best_key = key

    return best_key


def _infer_stock_key(keys: list[str]) -> str | None:
    explicit = _pick_key(keys, EXPLICIT_STOCK_KEYWORDS)
    if explicit:
        return explicit

    # Si "cantidad" aparece como columna exacta, usarla siempre como stock
    # independientemente de otras columnas operacionales
    for key in keys:
        if key == "cantidad":
            return key

    has_operational_columns = any(
        keyword in key for key in keys for keyword in OPERATIONAL_KEYWORDS
    )
    if has_operational_columns:
        return None

    return _pick_key(keys, AMBIGUOUS_STOCK_KEYWORDS)


def _is_summary_name(name: str, row: dict[str, Any]) -> bool:
    normalized_name = _norm(name)
    if normalized_name in SUMMARY_NAMES:
        return True
    if not normalized_name:
        return True

    normalized_text_values = [
        _norm(value) for value in row.values() if isinstance(value, str) and _norm(value)
    ]
    if any(value in SUMMARY_NAMES for value in normalized_text_values if value != normalized_name):
        return True

    numeric_values = [_safe_float(value) for key, value in row.items() if key != "sheet"]
    meaningful_numeric_values = [value for value in numeric_values if value not in (None, 0.0)]
    if normalized_name not in SUMMARY_NAMES and meaningful_numeric_values:
        return False

    name_text = str(name or "").strip()
    return name_text.isalpha() and name_text == name_text.upper()


def _looks_like_product_table(
    resolved_sheet: str | None,
    *,
    name_key: str | None,
    price_key: str | None,
    stock_key: str | None,
    cost_key: str | None,
    sku_key: str | None,
    category_key: str | None,
) -> bool:
    if not name_key:
        return False

    normalized_sheet = _norm(resolved_sheet)
    has_sheet_hint = any(keyword in normalized_sheet for keyword in SHEET_HINT_KEYWORDS)
    return any(
        (
            has_sheet_hint,
            price_key is not None,
            stock_key is not None,
            cost_key is not None,
            sku_key is not None,
            category_key is not None,
        )
    )


def build_product_candidates(
    datos: dict[str, Any],
    sheet_name: str | None = None,
    row_indexes: list[int] | None = None,
    default_category_name: str | None = None,
) -> tuple[list[ProductCandidate], str | None]:
    rows_raw, resolved_sheet = _select_document_rows(datos, sheet_name)
    dict_rows = [row for row in rows_raw if isinstance(row, dict)]
    if not dict_rows:
        return [], resolved_sheet

    normalized_rows = [_normalize_row(row) for row in dict_rows]
    keys = list({key for row in normalized_rows for key in row.keys()})
    if not keys:
        return [], resolved_sheet

    name_key = _pick_key(keys, NAME_KEYWORDS)
    if not name_key:
        return [], resolved_sheet

    price_key = _pick_key(keys, PRICE_KEYWORDS, PRICE_REJECT_KEYWORDS)
    stock_key = _infer_stock_key(keys)
    cost_key = _pick_key(keys, COST_KEYWORDS)
    sku_key = _pick_key(keys, SKU_KEYWORDS)
    category_key = _pick_key(keys, CATEGORY_KEYWORDS)
    description_key = _pick_key(keys, DESCRIPTION_KEYWORDS)
    if not _looks_like_product_table(
        resolved_sheet,
        name_key=name_key,
        price_key=price_key,
        stock_key=stock_key,
        cost_key=cost_key,
        sku_key=sku_key,
        category_key=category_key,
    ):
        return [], resolved_sheet

    if row_indexes:
        selected_indexes = [index for index in row_indexes if 0 <= index < len(normalized_rows)]
    else:
        selected_indexes = list(range(len(normalized_rows)))

    candidates: list[ProductCandidate] = []
    default_category = _normalize_category_name(default_category_name)

    for index in selected_indexes:
        row = normalized_rows[index]
        raw_name = str(row.get(name_key) or "").strip()
        if not raw_name or _is_summary_name(raw_name, row):
            continue

        price = _safe_float(row.get(price_key)) if price_key else None
        stock = _safe_float(row.get(stock_key)) if stock_key else None
        cost_price = _safe_float(row.get(cost_key)) if cost_key else None
        category_name = default_category or _normalize_category_name(row.get(category_key))
        description = (
            str(row.get(description_key)).strip()
            if description_key and row.get(description_key) not in (None, "")
            else None
        )
        sku_value = (
            str(row.get(sku_key)).strip()
            if sku_key and row.get(sku_key) not in (None, "")
            else None
        )

        candidates.append(
            ProductCandidate(
                row_index=index,
                name=raw_name,
                price=price,
                stock=stock,
                unit="unit",
                sku=sku_value or None,
                category_name=category_name,
                description=description,
                cost_price=cost_price,
                product_metadata={
                    "import_source": "importador_document",
                    "source_sheet": resolved_sheet,
                    "source_row_index": index,
                    "source_row": {
                        key: value for key, value in row.items() if value not in (None, "")
                    },
                },
            )
        )

    return candidates, resolved_sheet


def _upsert_stock_item(db: Session, tenant_id: UUID, product_id: str, qty: float) -> None:
    """Sincroniza stock_items con el primer almacén activo del tenant."""
    warehouse = (
        db.execute(
            select(Warehouse)
            .where(Warehouse.tenant_id == str(tenant_id), Warehouse.is_active.is_(True))
            .order_by(Warehouse.id)
            .limit(1)
        )
        .scalars()
        .first()
    )
    if not warehouse:
        return

    stock_item = (
        db.execute(
            select(StockItem).where(
                StockItem.tenant_id == str(tenant_id),
                StockItem.warehouse_id == str(warehouse.id),
                StockItem.product_id == product_id,
            )
        )
        .scalars()
        .first()
    )

    if stock_item:
        stock_item.qty = qty
        db.add(stock_item)
    else:
        db.add(
            StockItem(
                tenant_id=str(tenant_id),
                warehouse_id=str(warehouse.id),
                product_id=product_id,
                qty=qty,
            )
        )


def save_product_candidates(
    db: Session,
    tenant_id: UUID,
    candidates: list[ProductCandidate],
    source_document_id: UUID | None = None,
) -> dict[str, Any]:
    existing_products = (
        db.execute(select(Product).where(Product.tenant_id == tenant_id)).scalars().all()
    )
    existing_names = {_norm(product.name): product for product in existing_products if product.name}
    used_skus = {
        str(product.sku).strip().upper()
        for product in existing_products
        if product.sku and str(product.sku).strip()
    }

    created_ids: list[str] = []
    updated_ids: list[str] = []
    skipped_invalid: list[str] = []

    for candidate in candidates:
        normalized_name = _norm(candidate.name)
        if not normalized_name:
            skipped_invalid.append(candidate.name)
            continue

        if normalized_name in existing_names:
            # Producto existe — actualizar precio y stock siempre que el Excel traiga un valor
            existing = existing_names[normalized_name]
            if candidate.price is not None:
                existing.price = candidate.price
            if candidate.stock is not None:
                existing.stock = candidate.stock
                _upsert_stock_item(db, tenant_id, str(existing.id), candidate.stock)
            if candidate.cost_price is not None:
                existing.cost_price = candidate.cost_price
            db.add(existing)
            db.flush()
            updated_ids.append(str(existing.id))
            continue

        category_name = _normalize_category_name(candidate.category_name)
        category_id = _resolve_category_id(db, tenant_id, category_name) if category_name else None

        sku = candidate.sku.strip() if candidate.sku else None
        if sku and sku.upper() in used_skus:
            sku = None
        if not sku:
            sku = _generate_next_sku(db, tenant_id, category_name)

        metadata = dict(candidate.product_metadata or {})
        if source_document_id:
            metadata["source_document_id"] = str(source_document_id)

        product = Product(
            tenant_id=tenant_id,
            name=candidate.name,
            price=candidate.price if candidate.price is not None else 0.0,
            stock=candidate.stock if candidate.stock is not None else 0.0,
            unit=candidate.unit or "unit",
            sku=sku,
            category_id=category_id,
            description=candidate.description,
            cost_price=candidate.cost_price,
            active=True,
            product_metadata=metadata or None,
        )
        db.add(product)
        db.flush()

        # Sincronizar stock en stock_items con el almacén principal
        stock_qty = candidate.stock if candidate.stock is not None else 0.0
        _upsert_stock_item(db, tenant_id, str(product.id), stock_qty)

        existing_names[normalized_name] = product
        used_skus.add(str(product.sku).strip().upper())
        created_ids.append(str(product.id))

    return {
        "created": len(created_ids),
        "updated": len(updated_ids),
        "skipped_existing": 0,
        "skipped_invalid": len(skipped_invalid),
        "product_ids": created_ids + updated_ids,
        "skipped_names": [],
    }
