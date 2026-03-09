"""
set_product_units_from_packaging.py
=====================================
Actualiza Product.unit para que coincida con la unidad de empaque (purchase_packaging)
de cada ingrediente en recetas.

LÓGICA:
  Para cada producto que aparece en recipe_ingredients:
    - Si purchase_packaging es una unidad métrica (kg, g, lb, L, ml…) → Product.unit = esa unidad
    - Si purchase_packaging es una etiqueta custom (Cubeta, bloque, saco…) → Product.unit = esa etiqueta
    - Fallback: si no tiene empaque → usa RecipeIngredient.unit (unidad de receta)

RESULTADO:
  Harina        → "kg"
  Azucar        → "kg"
  Manteca veg.  → "kg"
  Margarina     → "kg"
  Mant. chancho → "lb"  (purchase_packaging = "libras" → normaliza a "lb")
  Huevos        → "Cubeta"
  Levadura      → "bloque"
  Agua          → "L"   (purchase_packaging = "litro" → normaliza a "L")
  Sal           → "kg"

USO:
  cd apps/backend
  python scripts/set_product_units_from_packaging.py [--dry-run] [--tenant-id UUID]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.orm import Session

from app.config.database import engine
from app.models.core.products import Product
from app.models.recipes import RecipeIngredient
from app.utils.unit_converter import normalize_unit_name, get_unit_type

# Unidades métricas conocidas (tras normalización)
_METRIC_UNITS = {"kg", "g", "lb", "oz", "ton", "mg", "L", "ml", "gal", "qt", "pt", "cup", "fl_oz", "tbsp", "tsp"}


def _resolve_unit(purchase_packaging: str | None, recipe_unit: str | None) -> str:
    """
    Decide qué unidad usar para Product.unit.
    Prioridad: purchase_packaging normalizado > recipe_unit normalizado > "unit"
    """
    # Intentar normalizar el empaque
    if purchase_packaging:
        pkg = purchase_packaging.strip()
        normalized = normalize_unit_name(pkg)
        unit_type = get_unit_type(normalized)
        if unit_type is not None:
            # Es una unidad métrica conocida → usar la versión normalizada
            return normalized
        else:
            # Es una etiqueta custom (Cubeta, bloque, saco…) → usarla como está
            return pkg

    # Fallback: usar la unidad de receta
    if recipe_unit:
        normalized = normalize_unit_name(recipe_unit.strip())
        if get_unit_type(normalized):
            return normalized
        return recipe_unit.strip()

    return "unit"


def run(dry_run: bool = False, tenant_filter: str | None = None):
    with Session(engine) as db:
        q = db.query(RecipeIngredient)
        if tenant_filter:
            # Llegar al tenant via recipe → join no directo, filtrar por product
            pass  # simplificado: aplica a todos los tenants

        ingredients = q.all()

        # Agrupar por product_id → tomar el empaque más representativo
        # (en caso de que el mismo producto esté en varias recetas con distinto empaque,
        #  elegimos el más frecuente)
        from collections import Counter
        product_packaging: dict[str, Counter] = {}
        product_recipe_unit: dict[str, str] = {}

        for ing in ingredients:
            pid = str(ing.product_id)
            pkg = (ing.purchase_packaging or "").strip()
            if pkg:
                product_packaging.setdefault(pid, Counter())[pkg] += 1
            if not product_recipe_unit.get(pid) and ing.unit:
                product_recipe_unit[pid] = ing.unit

        print(f"Productos con info de empaque: {len(product_packaging)}")
        print(f"\n{'Producto':<35} {'Unidad actual':<16} {'→ Nueva unidad':<16} {'Empaque fuente'}")
        print("-" * 85)

        changes = []
        for pid, pkg_counter in product_packaging.items():
            most_common_pkg = pkg_counter.most_common(1)[0][0]
            recipe_unit = product_recipe_unit.get(pid)
            new_unit = _resolve_unit(most_common_pkg, recipe_unit)

            q_prod = db.query(Product).filter(Product.id == pid)
            if tenant_filter:
                q_prod = q_prod.filter(Product.tenant_id == tenant_filter)
            prod = q_prod.first()

            if not prod:
                continue

            old_unit = prod.unit or "unit"
            if old_unit == new_unit:
                continue  # ya está bien

            print(f"{prod.name:<35} {old_unit:<16} {new_unit:<16} (empaque: {most_common_pkg})")
            changes.append((prod, new_unit))

        if not changes:
            print("Nada que cambiar — todos los productos ya tienen la unidad correcta.")
            return

        print(f"\nTotal a actualizar: {len(changes)} productos")

        if dry_run:
            print("\n[DRY RUN] No se modificó nada.")
            return

        print("\nAplicando cambios...")
        for prod, new_unit in changes:
            prod.unit = new_unit

        db.commit()
        print(f"Actualizado Product.unit para {len(changes)} productos.")
        print("\nRecuerda ejecutar también fix_production_unit_conversion.py para corregir el stock histórico.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setea Product.unit según unidad de empaque de recetas")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra cambios, no modifica BD")
    parser.add_argument("--tenant-id", help="Limitar a un tenant específico")
    args = parser.parse_args()
    run(dry_run=args.dry_run, tenant_filter=args.tenant_id)
