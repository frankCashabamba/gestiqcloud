"""Sync importador costing documents into production recipes."""

from __future__ import annotations

import re
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.importador import ImpDocumento
from app.models.recipes import Recipe, RecipeIngredient
from app.services.unit_catalog_service import normalize_operational_unit
from app.shared.utils import safe_decimal as _as_decimal


def _normalize_unit(unit: str | None) -> str:
    return normalize_operational_unit(unit)


RECIPE_NAME_KEYS = (
    "nombre_de_la_receta",
    "nombre_receta",
    "nombre de la receta",
    "nombre",
)

YIELD_KEYS = (
    "n_de_porciones",
    "n\u00b0_de_porciones",
    "porciones",
    "yield",
    "rendimiento",
)

WASTE_KEYS = (
    "merma",
    "merma_(recomendado_10%)",
)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower())
    return slug.strip("-") or "sin-nombre"


def _pick_first(d: dict, *keys: str):
    for key in keys:
        value = d.get(key)
        if value not in (None, ""):
            return value
    return None


def _get_sheet_metadata(doc_data: dict, sheet_name: str | None = None) -> dict:
    metadata_by_sheet = doc_data.get("metadata_por_hoja") or {}
    if sheet_name and isinstance(metadata_by_sheet, dict):
        sheet_meta = metadata_by_sheet.get(sheet_name)
        if isinstance(sheet_meta, dict):
            return sheet_meta

    active_sheet = doc_data.get("sheet_usada")
    active_meta = doc_data.get("metadata") or {}
    if (
        sheet_name
        and active_sheet
        and str(sheet_name).strip() == str(active_sheet).strip()
        and isinstance(active_meta, dict)
    ):
        return active_meta
    if sheet_name:
        return {}
    return active_meta if isinstance(active_meta, dict) else {}


def _get_rows(doc_data: dict, sheet_override: str | None = None) -> tuple[list[dict], str | None]:
    """Return the selected sheet rows when available."""
    sheet_used = sheet_override or doc_data.get("sheet_usada")
    rows_by_sheet = doc_data.get("filas_por_hoja") or {}
    if sheet_used and isinstance(rows_by_sheet, dict) and sheet_used in rows_by_sheet:
        rows = rows_by_sheet.get(sheet_used) or []
        return rows if isinstance(rows, list) else [], str(sheet_used)
    rows = doc_data.get("filas") or []
    return rows if isinstance(rows, list) else [], str(sheet_used) if sheet_used else None


def _get_recipe_name_from_rows(rows: list[dict]) -> str | None:
    for row in rows[:20]:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            key_norm = str(key or "").strip().lower()
            if key_norm in RECIPE_NAME_KEYS and value not in (None, ""):
                return str(value).strip()
    return None


def _get_recipe_name(
    doc_data: dict,
    filename: str,
    *,
    rows: list[dict] | None = None,
    sheet_override: str | None = None,
) -> str:
    metadata = _get_sheet_metadata(doc_data, sheet_override)
    row_name = _get_recipe_name_from_rows(rows or [])
    return (
        _pick_first(metadata, *RECIPE_NAME_KEYS)
        or row_name
        or (
            sheet_override.strip()
            if isinstance(sheet_override, str) and sheet_override.strip()
            else None
        )
        or doc_data.get("nombre_receta")
        or doc_data.get("sheet_usada")
        or filename.split("::")[0].split(".")[0]
    )


def _get_yield(doc_data: dict, sheet_override: str | None = None) -> int:
    metadata = _get_sheet_metadata(doc_data, sheet_override)
    value = _pick_first(metadata, *YIELD_KEYS)
    try:
        if value is None:
            return 1
        return int(float(value))
    except Exception:
        return 1


def _get_waste_pct(doc_data: dict, sheet_override: str | None = None) -> Decimal:
    metadata = _get_sheet_metadata(doc_data, sheet_override)
    value = _pick_first(metadata, *WASTE_KEYS)
    waste = _as_decimal(value)
    if waste > 1:
        return waste
    return waste * 100


def _find_or_create_product(
    db: Session,
    tenant_id: UUID,
    name: str,
    unit: str | None,
    cost_price: Decimal | None,
) -> Product:
    product = (
        db.query(Product)
        .filter(Product.tenant_id == tenant_id)
        .filter(Product.name.ilike(name))
        .first()
    )
    if product:
        return product

    product = Product(
        tenant_id=tenant_id,
        name=name,
        unit=unit or "unit",
        cost_price=cost_price if cost_price is not None else None,
        active=True,
    )
    db.add(product)
    db.flush()
    return product


def _compute_ingredient_cost(
    qty: Decimal, qty_per_package: Decimal, package_cost: Decimal
) -> Decimal:
    if qty_per_package <= 0:
        return Decimal("0")
    return (qty * package_cost) / qty_per_package


def get_available_recipe_sheets(doc_data: dict) -> list[str]:
    if not isinstance(doc_data, dict):
        return []

    rows_by_sheet = doc_data.get("filas_por_hoja") or {}
    if isinstance(rows_by_sheet, dict) and rows_by_sheet:
        return [str(sheet) for sheet in rows_by_sheet.keys() if str(sheet).strip()]

    # Fallback: detect distinct sheets from _sheet field in filas
    filas = doc_data.get("filas") or []
    if isinstance(filas, list):
        seen: list[str] = []
        seen_set: set[str] = set()
        for row in filas:
            if isinstance(row, dict):
                sname = str(row.get("_sheet") or "").strip()
                if sname and sname not in seen_set:
                    seen_set.add(sname)
                    seen.append(sname)
        if seen:
            return seen

    sheets = doc_data.get("hojas") or []
    if isinstance(sheets, list):
        return [str(sheet) for sheet in sheets if str(sheet).strip()]

    active_sheet = doc_data.get("sheet_usada")
    if active_sheet:
        return [str(active_sheet)]
    return []


def _enrich_data_from_doc(data: dict, doc: ImpDocumento) -> dict:
    """Backfill metadata_por_hoja and filas_por_hoja from sheet_profiles_json.

    Older documents don't have these keys in datos_extraidos; this reads them
    from the separate sheet_profiles_json column so yield/metadata extraction works.
    """
    enriched = False

    if "metadata_por_hoja" not in data:
        profiles = doc.sheet_profiles_json or {}
        if isinstance(profiles, dict):
            meta = {
                sname: prof.get("kv_pairs", {})
                for sname, prof in profiles.items()
                if isinstance(prof, dict) and prof.get("kv_pairs")
            }
            if meta:
                data = dict(data)
                data["metadata_por_hoja"] = meta
                enriched = True

    if "filas_por_hoja" not in data:
        filas = data.get("filas") or []
        filas_por_hoja: dict[str, list] = {}
        for row in filas:
            if isinstance(row, dict):
                sname = str(row.get("_sheet") or "")
                if sname:
                    filas_por_hoja.setdefault(sname, []).append(row)
        if filas_por_hoja:
            if not enriched:
                data = dict(data)
            data["filas_por_hoja"] = filas_por_hoja

    return data


def upsert_recipe_from_import(
    doc: ImpDocumento, db: Session, *, sheet_override: str | None = None
) -> tuple[UUID | None, bool]:
    """Create or update one production recipe from one import sheet."""
    data = doc.datos_confirmados or doc.datos_extraidos or {}
    if not isinstance(data, dict):
        return None, False

    data = _enrich_data_from_doc(data, doc)

    rows, sheet_used = _get_rows(data, sheet_override=sheet_override)
    if not rows:
        return None, False

    recipe_name = _get_recipe_name(data, doc.nombre_archivo, rows=rows, sheet_override=sheet_used)
    if not recipe_name:
        recipe_name = "Receta sin nombre"

    yield_qty = _get_yield(data, sheet_used)
    waste_pct = _get_waste_pct(data, sheet_used)
    metadata = _get_sheet_metadata(data, sheet_used)

    unit_cost_meta = _as_decimal(metadata.get("costo_unitario_ingredientes") or 0)
    suggested_price_meta = _as_decimal(metadata.get("precio_de_venta_unitario") or 0)

    product_final = _find_or_create_product(
        db,
        doc.tenant_id,
        recipe_name,
        unit="unit",
        cost_price=unit_cost_meta or None,
    )
    if suggested_price_meta > 0:
        product_final.suggested_price = suggested_price_meta
        product_final.use_suggested_price = True

    was_new = False
    recipe = (
        db.query(Recipe)
        .filter(Recipe.tenant_id == doc.tenant_id)
        .filter(Recipe.name.ilike(recipe_name))
        .first()
    )
    if not recipe:
        was_new = True
        recipe = Recipe(
            tenant_id=doc.tenant_id,
            product_id=product_final.id,
            name=recipe_name,
            yield_qty=yield_qty,
            waste_pct=waste_pct,
            total_cost=Decimal("0"),
            prep_time_minutes=None,
            baking_time_minutes=None,
            oven_temp_celsius=None,
            rest_time_minutes=None,
        )
        db.add(recipe)
        db.flush()
    else:
        recipe.product_id = product_final.id
        recipe.yield_qty = yield_qty
        recipe.waste_pct = waste_pct

    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe.id).delete()

    total_cost = Decimal("0")
    line_order = 0

    for row in rows:
        if not isinstance(row, dict):
            continue

        name = row.get("ingredientes") or row.get("ingredient") or row.get("nombre")
        if not name:
            name = row.get("descripci\u00f3n") or row.get("descripcion") or row.get("description")
        if not name or not str(name).strip():
            continue

        qty = _as_decimal(
            row.get("cantidad_(ml_/gr)") or row.get("cantidad") or row.get("qty") or 0
        )
        unit = _normalize_unit(row.get("unidad_(ml_/_gr)") or row.get("unidad"))

        package_cost = _as_decimal(
            row.get("inversi\u00f3n_en_compra")
            or row.get("inversion_en_compra")
            or row.get("costo_compra")
            or 0
        )
        qty_per_package = _as_decimal(
            row.get("peso_neto_(gramos,_militros/_unidades)")
            or row.get("contenido_neto_(unidades)")
            or row.get("contenido_neto")
            or row.get("rendimiento__real_(*0=1)")
            or row.get("rendimiento_real_(*0=1)")
            or 0
        )

        direct_amount = _as_decimal(row.get("importe") or 0)
        if qty_per_package <= 0 and package_cost <= 0 and direct_amount > 0:
            package_cost = direct_amount
            if qty <= 0:
                qty = Decimal("1")
            qty_per_package = qty

        packaging = (
            row.get("unidad_de_compra")
            or row.get("dimensi\u00f3n_/_medida")
            or row.get("dimension_medida")
        )

        product = _find_or_create_product(
            db, doc.tenant_id, str(name).strip(), unit=None, cost_price=None
        )
        ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            product_id=product.id,
            qty=qty if qty > 0 else Decimal("1"),
            unit=unit,
            purchase_packaging=str(packaging) if packaging else None,
            qty_per_package=(
                qty_per_package if qty_per_package > 0 else qty if qty > 0 else Decimal("1")
            ),
            package_unit=unit,
            package_cost=package_cost,
            line_order=line_order,
            notes=None,
        )
        db.add(ingredient)
        total_cost += _compute_ingredient_cost(
            ingredient.qty, ingredient.qty_per_package, package_cost
        )
        line_order += 1

    recipe.total_cost = total_cost
    db.flush()
    return recipe.id, was_new
