"""
Internal API for the products module.

Used by other modules (e.g. importador) to interact with products without
importing SQLAlchemy models directly. All public functions accept/return plain
Python dicts or primitive types so the boundary stays model-free for callers.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.inventory.stock import StockItem
from app.models.inventory.warehouse import Warehouse

# ---------------------------------------------------------------------------
# Internal helpers (not exported)
# ---------------------------------------------------------------------------


def _norm(value: Any) -> str:
    text_val = unicodedata.normalize("NFKD", str(value or ""))
    text_val = "".join(ch for ch in text_val if not unicodedata.combining(ch))
    text_val = text_val.strip().lower()
    text_val = re.sub(r"[^a-z0-9]+", " ", text_val)
    return re.sub(r"\s+", " ", text_val).strip()


def _normalize_category_name(value: str | None) -> str | None:
    if value is None:
        return None
    name = value.strip()
    return name or None


def _resolve_category_id(db: Session, tenant_id: str, category_name: str | None) -> UUID | None:
    if not category_name:
        return None
    category = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.name == category_name,
        )
        .first()
    )
    if category:
        return category.id
    category = ProductCategory(tenant_id=tenant_id, name=category_name)
    db.add(category)
    db.flush()
    return category.id


def _generate_next_sku(db: Session, tenant_id: str, categoria: str | None) -> str:
    """Genera SKU automático: {PREFIJO}-{SECUENCIA}"""
    if categoria:
        prefix = re.sub(r"[^A-Z]", "", categoria.upper())[:3] or "PRO"
    else:
        prefix = "PRO"

    result = db.execute(
        text(
            "SELECT sku FROM products "
            "WHERE tenant_id = :tid AND sku LIKE :pattern "
            "ORDER BY sku DESC LIMIT 1"
        ),
        {"tid": str(tenant_id), "pattern": f"{prefix}-%"},
    ).fetchone()

    if result and result[0]:
        match = re.search(r"-(\d+)$", result[0])
        next_num = int(match.group(1)) + 1 if match else 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:04d}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_product_by_sku(db: Session, tenant_id: str, sku: str) -> dict | None:
    """Return a product dict for the given tenant+SKU, or None if not found."""
    product = (
        db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.sku == sku,
            )
        )
        .scalars()
        .first()
    )
    if not product:
        return None
    return {
        "id": str(product.id),
        "name": product.name,
        "sku": product.sku,
        "price": float(product.price) if product.price is not None else None,
        "cost_price": float(product.cost_price) if product.cost_price is not None else None,
        "stock": float(product.stock) if product.stock is not None else 0.0,
        "unit": product.unit,
        "active": product.active,
        "category_id": str(product.category_id) if product.category_id else None,
    }


def upsert_stock_from_import(
    db: Session,
    tenant_id: UUID,
    product_id: str,
    qty: float,
) -> None:
    """Sync stock_items for a product against the first active warehouse.

    Auto-creates 'Almacén Principal' when the tenant has no active warehouse yet.
    Handles the in-session pending-add guard and IntegrityError retry so the
    importador doesn't need to know about StockItem / Warehouse internals.
    """
    warehouse = (
        db.execute(
            select(Warehouse)
            .where(Warehouse.tenant_id == tenant_id, Warehouse.is_active.is_(True))
            .order_by(Warehouse.id)
            .limit(1)
        )
        .scalars()
        .first()
    )
    if not warehouse:
        warehouse = Warehouse(
            tenant_id=tenant_id,
            code="PRINCIPAL",
            name="Almacén Principal",
            is_active=True,
        )
        db.add(warehouse)
        db.flush()

    # Guard: detect a StockItem already pending in the current unit-of-work
    pending_stock_item = next(
        (
            item
            for item in db.new
            if isinstance(item, StockItem)
            and item.tenant_id == tenant_id
            and item.warehouse_id == warehouse.id
            and str(item.product_id) == str(product_id)
            and item.lot is None
            and item.expires_at is None
        ),
        None,
    )
    if pending_stock_item is not None:
        pending_stock_item.qty = qty
        return

    stock_item = (
        db.execute(
            select(StockItem).where(
                StockItem.tenant_id == tenant_id,
                StockItem.warehouse_id == warehouse.id,
                StockItem.product_id == product_id,
                StockItem.lot.is_(None),
                StockItem.expires_at.is_(None),
            )
        )
        .scalars()
        .first()
    )

    if stock_item:
        stock_item.qty = qty
        db.add(stock_item)
    else:
        stock_item = StockItem(
            tenant_id=tenant_id,
            warehouse_id=warehouse.id,
            product_id=product_id,
            qty=qty,
            lot=None,
            expires_at=None,
        )
        try:
            with db.begin_nested():
                db.add(stock_item)
                db.flush()
        except IntegrityError:
            stock_item = (
                db.execute(
                    select(StockItem).where(
                        StockItem.tenant_id == tenant_id,
                        StockItem.warehouse_id == warehouse.id,
                        StockItem.product_id == product_id,
                        StockItem.lot.is_(None),
                        StockItem.expires_at.is_(None),
                    )
                )
                .scalars()
                .first()
            )
            if stock_item is None:
                raise
            stock_item.qty = qty
            db.add(stock_item)


def save_product_candidates_from_import(
    db: Session,
    tenant_id: UUID,
    candidates: list,  # list[ProductCandidate] — imported locally to avoid circular
    source_document_id: UUID | None = None,
) -> dict[str, Any]:
    """Persist a list of ProductCandidate objects for a tenant.

    Owns the Product + StockItem upsert logic so that product_import_service.py
    no longer needs to import Product, StockItem, or Warehouse directly.

    Returns the same summary dict as the previous save_product_candidates().
    """
    existing_products = (
        db.execute(select(Product).where(Product.tenant_id == tenant_id)).scalars().all()
    )
    existing_names = {_norm(p.name): p for p in existing_products if p.name}
    used_skus = {
        str(p.sku).strip().upper() for p in existing_products if p.sku and str(p.sku).strip()
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
            existing = existing_names[normalized_name]
            if candidate.price is not None:
                existing.price = candidate.price
            if candidate.stock is not None:
                existing.stock = candidate.stock
                upsert_stock_from_import(db, tenant_id, str(existing.id), candidate.stock)
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

        stock_qty = candidate.stock if candidate.stock is not None else 0.0
        upsert_stock_from_import(db, tenant_id, str(product.id), stock_qty)

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
