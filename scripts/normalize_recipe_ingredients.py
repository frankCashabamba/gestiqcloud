#!/usr/bin/env python3
"""
Normaliza datos legacy en recipe_ingredients.

Por defecto corre en modo dry-run (no guarda cambios).

Uso:
  python scripts/normalize_recipe_ingredients.py
  python scripts/normalize_recipe_ingredients.py --apply
  python scripts/normalize_recipe_ingredients.py --tenant-id <uuid> --apply
  python scripts/normalize_recipe_ingredients.py --apply --fix-zero-qty
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Ensure repository root is importable when running "python scripts/..."
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND_ROOT = ROOT / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from apps.backend.app.config.database import make_db_url
VALID_UNITS = {
    "kg",
    "g",
    "lb",
    "oz",
    "ton",
    "mg",
    "L",
    "ml",
    "gal",
    "qt",
    "pt",
    "cup",
    "fl_oz",
    "tbsp",
    "tsp",
    "uds",
    "unidades",
    "pcs",
}


def _normalize_unit(raw: str | None) -> str:
    if raw is None:
        return "uds"
    s = str(raw).strip()
    if not s:
        return "uds"

    low = s.lower()
    low = low.replace(",", ".")
    low = re.sub(r"\s+", " ", low)

    if low in {u.lower() for u in VALID_UNITS}:
        # Keep canonical case used in schema
        if low == "l":
            return "L"
        return low

    # Remove numeric prefixes/suffixes: "1 paquete", "2.5 kg"
    cleaned = re.sub(r"^[\d\.,\s]+", "", low).strip()
    cleaned = re.sub(r"[\d\.,\s]+$", "", cleaned).strip()

    # Common aliases
    if cleaned in {"gr", "gr.", "grs", "gramo", "gramos"}:
        return "g"
    if cleaned in {"k", "kg.", "kilo", "kilos", "kilogramo", "kilogramos"}:
        return "kg"
    if cleaned in {"l", "lt", "lts", "litro", "litros"}:
        return "L"
    if cleaned in {"cc", "cm3"}:
        return "ml"
    if cleaned in {"unidad", "unid", "und", "u", "uni", "pz", "pza", "pzas"}:
        return "uds"
    if cleaned in {"paquete", "pack", "paq", "bolsa", "caja"}:
        return "uds"

    # If still contains package words
    if any(tok in low for tok in ("paquete", "pack", "bolsa", "caja", "unidad", "und")):
        return "uds"

    # Unknown fallback to generic count unit
    return "uds"


@dataclass
class Change:
    ingredient_id: str
    recipe_id: str
    field: str
    old: str
    new: str


def _iter_ingredients(session: Session, tenant_id: str | None) -> Iterable[dict]:
    base_sql = """
        SELECT
            ri.id,
            ri.recipe_id,
            ri.qty,
            ri.unit,
            ri.purchase_packaging,
            ri.qty_per_package,
            ri.package_unit
        FROM recipe_ingredients ri
        JOIN recipes r ON r.id = ri.recipe_id
    """
    params: dict[str, str] = {}
    if tenant_id:
        base_sql += " WHERE r.tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    rows = session.execute(text(base_sql), params).mappings().all()
    return [dict(r) for r in rows]


def normalize(
    *,
    tenant_id: str | None,
    apply_changes: bool,
    fix_zero_qty: bool,
    fix_null_packaging: bool,
) -> int:
    engine = create_engine(make_db_url())
    changes: list[Change] = []
    changed_rows = 0

    with Session(engine) as session:
        ingredients = list(_iter_ingredients(session, tenant_id))
        for ing in ingredients:
            row_changed = False
            pending_update: dict[str, object] = {}

            old_unit = ing.get("unit")
            new_unit = _normalize_unit(old_unit)
            if (old_unit or "") != new_unit:
                changes.append(
                    Change(
                        str(ing["id"]),
                        str(ing["recipe_id"]),
                        "unit",
                        str(old_unit),
                        str(new_unit),
                    )
                )
                pending_update["unit"] = new_unit
                row_changed = True

            old_pkg_unit = ing.get("package_unit")
            new_pkg_unit = _normalize_unit(old_pkg_unit)
            if (old_pkg_unit or "") != new_pkg_unit:
                changes.append(
                    Change(
                        str(ing["id"]),
                        str(ing["recipe_id"]),
                        "package_unit",
                        str(old_pkg_unit),
                        str(new_pkg_unit),
                    )
                )
                pending_update["package_unit"] = new_pkg_unit
                row_changed = True

            if fix_null_packaging and not ing.get("purchase_packaging"):
                changes.append(
                    Change(
                        str(ing["id"]),
                        str(ing["recipe_id"]),
                        "purchase_packaging",
                        str(ing.get("purchase_packaging")),
                        "N/A",
                    )
                )
                pending_update["purchase_packaging"] = "N/A"
                row_changed = True

            current_qty = ing.get("qty")
            if fix_zero_qty and (current_qty is None or Decimal(str(current_qty)) <= 0):
                changes.append(
                    Change(
                        str(ing["id"]),
                        str(ing["recipe_id"]),
                        "qty",
                        str(current_qty),
                        "0.0001",
                    )
                )
                pending_update["qty"] = Decimal("0.0001")
                row_changed = True

            if row_changed:
                if apply_changes and pending_update:
                    set_parts = []
                    params = {"id": str(ing["id"])}
                    for k, v in pending_update.items():
                        set_parts.append(f"{k} = :{k}")
                        params[k] = v
                    sql = f"UPDATE recipe_ingredients SET {', '.join(set_parts)} WHERE id = :id"
                    session.execute(text(sql), params)
                changed_rows += 1

        print(f"Ingredientes evaluados: {len(ingredients)}")
        print(f"Filas con cambios: {changed_rows}")
        print(f"Cambios detectados: {len(changes)}")

        preview = changes[:30]
        for c in preview:
            print(
                f"- ingredient={c.ingredient_id} recipe={c.recipe_id} "
                f"{c.field}: '{c.old}' -> '{c.new}'"
            )
        if len(changes) > len(preview):
            print(f"... y {len(changes) - len(preview)} cambios más")

        if apply_changes:
            session.commit()
            print("Cambios aplicados.")
        else:
            session.rollback()
            print("Dry-run completado. No se guardaron cambios.")

    return changed_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", dest="tenant_id", default=None)
    parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD")
    parser.add_argument(
        "--fix-zero-qty",
        action="store_true",
        help="Corrige qty <= 0 a 0.0001 (desactivado por defecto)",
    )
    parser.add_argument(
        "--fix-null-packaging",
        action="store_true",
        help="Rellena purchase_packaging nulo con 'N/A'",
    )
    args = parser.parse_args()

    normalize(
        tenant_id=args.tenant_id,
        apply_changes=args.apply,
        fix_zero_qty=args.fix_zero_qty,
        fix_null_packaging=args.fix_null_packaging,
    )


if __name__ == "__main__":
    main()
