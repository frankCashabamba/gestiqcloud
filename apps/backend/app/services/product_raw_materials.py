from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.config.database import IS_SQLITE
from app.models.core.products import Product
from app.models.recipes import Recipe, RecipeIngredient
from app.models.tenant import Tenant
from app.services.field_config import resolve_sector_code
from app.services.unit_catalog_service import normalize_operational_unit

logger = logging.getLogger(__name__)


def ensure_products_raw_material_column(db: Session) -> None:
    cached = db.info.get("products_raw_material_column_ready")
    if cached is True:
        return

    inspector = inspect(db.bind)
    schema = None if IS_SQLITE else "public"
    columns = {col["name"] for col in inspector.get_columns("products", schema=schema)}
    if "is_raw_material" in columns:
        db.info["products_raw_material_column_ready"] = True
        return

    if IS_SQLITE:
        db.execute(
            text(
                "ALTER TABLE products "
                "ADD COLUMN is_raw_material BOOLEAN NOT NULL DEFAULT 0"
            )
        )
    else:
        db.execute(
            text(
                "ALTER TABLE public.products "
                "ADD COLUMN IF NOT EXISTS is_raw_material BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
    db.commit()
    db.info["products_raw_material_column_ready"] = True


def tenant_sector_code(db: Session, tenant_id: UUID | str | None) -> str:
    if not tenant_id:
        return "default"
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        tenant = db.get(Tenant, str(tenant_id))
    raw_sector = getattr(tenant, "sector_template_name", None) if tenant else None
    return resolve_sector_code(db, raw_sector or "default")


def is_generic_inventory_unit(unit: str | None) -> bool:
    return str(unit or "").strip().lower() in {"", "-", "unit", "units"}


def preferred_inventory_unit_from_recipe_line(
    unit: str | None, package_unit: str | None
) -> str | None:
    for raw_unit in (package_unit, unit):
        normalized = normalize_operational_unit(raw_unit, default="uds")
        if normalized and normalized != "uds":
            return normalized
    return None


def validate_raw_material_unit(
    db: Session,
    *,
    tenant_id: UUID | str | None,
    is_raw_material: bool,
    unit: str | None,
) -> None:
    if not is_raw_material:
        return
    if tenant_sector_code(db, tenant_id) != "panaderia":
        return
    if is_generic_inventory_unit(unit):
        raise HTTPException(
            status_code=400,
            detail=(
                "Las materias primas de panaderia deben usar una unidad operativa "
                "explicita como kg, g, L, ml o uds."
            ),
        )


def sync_product_as_raw_material_from_recipe_line(
    db: Session,
    *,
    tenant_id: UUID | str | None,
    product: Product | None,
    unit: str | None,
    package_unit: str | None,
) -> bool:
    if product is None:
        return False

    changed = False
    if not bool(getattr(product, "is_raw_material", False)):
        product.is_raw_material = True
        changed = True

    if tenant_sector_code(db, tenant_id) == "panaderia" and is_generic_inventory_unit(product.unit):
        preferred_unit = preferred_inventory_unit_from_recipe_line(unit, package_unit)
        if preferred_unit and product.unit != preferred_unit:
            product.unit = preferred_unit
            changed = True

    if changed:
        db.add(product)
    return changed


def backfill_bakery_raw_material_products(db: Session) -> int:
    ensure_products_raw_material_column(db)

    bakery_tenants = {
        tenant.id
        for tenant in db.query(Tenant).all()
        if resolve_sector_code(db, getattr(tenant, "sector_template_name", None) or "default")
        == "panaderia"
    }
    if not bakery_tenants:
        return 0

    rows = (
        db.query(RecipeIngredient, Recipe)
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .filter(Recipe.tenant_id.in_(bakery_tenants))
        .all()
    )
    if not rows:
        return 0

    by_product: dict[tuple[UUID, UUID], list[RecipeIngredient]] = defaultdict(list)
    for ingredient, recipe in rows:
        by_product[(recipe.tenant_id, ingredient.product_id)].append(ingredient)

    changed = 0
    for (tenant_id, product_id), ingredients in by_product.items():
        product = (
            db.query(Product)
            .filter(Product.tenant_id == tenant_id, Product.id == product_id)
            .first()
        )
        if product is None:
            continue
        changed_before = bool(getattr(product, "is_raw_material", False))
        unit_before = str(product.unit or "")

        preferred_unit = None
        for ingredient in ingredients:
            preferred_unit = preferred_inventory_unit_from_recipe_line(
                ingredient.unit, ingredient.package_unit
            )
            if preferred_unit:
                break

        sync_product_as_raw_material_from_recipe_line(
            db,
            tenant_id=tenant_id,
            product=product,
            unit=ingredients[0].unit if ingredients else None,
            package_unit=preferred_unit,
        )
        if bool(getattr(product, "is_raw_material", False)) != changed_before or str(
            product.unit or ""
        ) != unit_before:
            changed += 1

    if changed:
        db.commit()
        logger.info("Backfilled bakery raw materials for %s products", changed)
    return changed
