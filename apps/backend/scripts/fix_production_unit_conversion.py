"""
fix_production_unit_conversion.py
==================================
Corrección retroactiva del bug de conversión de unidades en producción.

PROBLEMA:
  Al completar una orden de producción, el sistema descontaba qty_consumed del
  stock directamente en la unidad de la receta (ej: 500 g), sin convertir a la
  unidad del producto (ej: kg). Resultado: cada producción descontaba 500 kg
  en lugar de 0.5 kg → stock muy negativo.

QUÉ HACE ESTE SCRIPT:
  1. Busca todos los stock_moves de tipo "production_consume".
  2. Para cada move, obtiene la línea de orden de producción (via stock_move_id).
  3. Compara la unidad de la línea (receta) vs la unidad del producto (stock).
  4. Si son compatibles y distintas, calcula la diferencia.
  5. Crea un stock_move de ajuste (kind="unit_conv_fix") por la diferencia.
  6. Actualiza stock_items.qty y products.stock.

USO:
  cd apps/backend
  python scripts/fix_production_unit_conversion.py [--dry-run] [--tenant-id UUID]

  --dry-run     Solo muestra qué haría, sin modificar la BD.
  --tenant-id   Limita la corrección a un tenant específico.
"""

import argparse
import sys
import os
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

# Ajusta el path para importar la app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.config.database import engine
from app.models.inventory.stock import StockItem, StockMove
from app.models.production._production_order import ProductionOrder, ProductionOrderLine
from app.models.core.products import Product
from app.models.recipes import RecipeIngredient
from app.utils.unit_converter import are_compatible_units, convert


def _calc_correct_stock_qty(
    qty_consumed: float,    # qty consumida (en unidad de receta, ej: 170 g)
    line_unit: str,         # unidad de la receta (ej: "g")
    product_unit: str,      # unidad del producto/stock (ej: "kg" o "bloque")
    recipe_ingredient: RecipeIngredient | None = None,
) -> float:
    """
    Calcula la qty correcta a descontar del stock, en product_unit.

    Estrategia 1 — conversión métrica estándar: g → kg, lb → oz, etc.
    Estrategia 2 — unidades de empaque: g → bloque (via qty_per_package),
                   uds → Cubeta (via qty_per_package), etc.
    """
    lu = (line_unit or "unit").strip()
    pu = (product_unit or "unit").strip()

    if lu == pu:
        return qty_consumed

    # Estrategia 1: unidades métricas compatibles
    if are_compatible_units(lu, pu):
        try:
            return convert(qty_consumed, lu, pu)
        except ValueError:
            pass

    # Estrategia 2: empaque (bloque, Cubeta, etc.) vía qty_per_package
    if recipe_ingredient and float(recipe_ingredient.qty_per_package or 0) > 0:
        pkg_unit = (recipe_ingredient.package_unit or "").strip()
        pkg_qty = float(recipe_ingredient.qty_per_package)
        qty_in_pkg_unit = qty_consumed
        if pkg_unit and pkg_unit != lu and are_compatible_units(lu, pkg_unit):
            try:
                qty_in_pkg_unit = convert(qty_consumed, lu, pkg_unit)
            except ValueError:
                pass
        return qty_in_pkg_unit / pkg_qty

    return qty_consumed  # fallback: sin conversión


def run(dry_run: bool = False, tenant_filter: str | None = None):
    with Session(engine) as db:
        # Obtener todos los moves de production_consume
        q = db.query(StockMove).filter(StockMove.kind == "production_consume")
        if tenant_filter:
            q = q.filter(StockMove.tenant_id == tenant_filter)
        moves = q.all()

        print(f"Encontrados {len(moves)} stock_moves de tipo production_consume")

        corrections: dict[str, float] = {}  # product_id → delta acumulado por warehouse
        corrections_detail: list[dict] = []
        skipped = 0
        no_line = 0

        for move in moves:
            # Buscar la línea de producción asociada
            line = (
                db.query(ProductionOrderLine)
                .filter(ProductionOrderLine.stock_move_id == str(move.id))
                .first()
            )
            if not line:
                no_line += 1
                continue

            product = (
                db.query(Product)
                .filter(Product.id == str(move.product_id))
                .first()
            )
            if not product:
                skipped += 1
                continue

            line_unit = (line.unit or "unit").strip()
            product_unit = (product.unit or "unit").strip()

            if line_unit == product_unit:
                skipped += 1
                continue

            # Buscar RecipeIngredient para conversión por empaque (bloque, Cubeta, etc.)
            order = db.query(ProductionOrder).filter(
                ProductionOrder.id == str(line.order_id)
            ).first()
            recipe_ingredient = None
            if order:
                recipe_ingredient = (
                    db.query(RecipeIngredient)
                    .filter(
                        RecipeIngredient.recipe_id == order.recipe_id,
                        RecipeIngredient.product_id == str(move.product_id),
                    )
                    .first()
                )

            abs_wrong = abs(float(move.qty))
            correct_qty = _calc_correct_stock_qty(
                abs_wrong, line_unit, product_unit, recipe_ingredient
            )
            delta = abs_wrong - correct_qty  # positivo → agregar al stock
            if abs(delta) < 1e-9:
                skipped += 1
                continue

            key = f"{move.tenant_id}:{move.warehouse_id}:{move.product_id}"
            corrections[key] = corrections.get(key, 0.0) + delta
            corrections_detail.append({
                "move_id": str(move.id),
                "product": product.name,
                "product_unit": product_unit,
                "line_unit": line_unit,
                "wrong_qty": -abs_wrong,
                "correct_qty": -correct_qty,
                "delta": delta,
                "tenant_id": str(move.tenant_id),
                "warehouse_id": str(move.warehouse_id),
                "product_id": str(move.product_id),
            })

        print(f"\nSin línea asociada: {no_line}")
        print(f"Sin conversión necesaria: {skipped}")
        print(f"Productos a corregir: {len(corrections)}\n")

        if not corrections:
            print("Nada que corregir.")
            return

        # Mostrar resumen por producto
        summary: dict[str, dict] = {}
        for d in corrections_detail:
            k = d["product_id"]
            if k not in summary:
                summary[k] = {"name": d["product"], "unit": d["product_unit"],
                               "line_unit": d["line_unit"], "total_delta": 0.0, "moves": 0}
            summary[k]["total_delta"] += d["delta"]
            summary[k]["moves"] += 1

        print(f"{'Producto':<30} {'Unidad receta':<15} {'Unidad stock':<14} {'Moves':>6} {'Corrección':>12}")
        print("-" * 80)
        for s in summary.values():
            print(f"{s['name']:<30} {s['line_unit']:<15} {s['unit']:<14} {s['moves']:>6} {s['total_delta']:>+12.4f}")

        if dry_run:
            print("\n[DRY RUN] No se modificó nada.")
            return

        print("\nAplicando correcciones...")
        applied = 0

        for d in corrections_detail:
            # Crear move de ajuste
            adj_move = StockMove(
                tenant_id=d["tenant_id"],
                product_id=d["product_id"],
                warehouse_id=d["warehouse_id"],
                qty=d["delta"],
                kind="unit_conv_fix",
                tentative=False,
                posted=True,
                ref_type="script_fix",
                ref_id="fix_production_unit_conversion",
                occurred_at=datetime.utcnow(),
            )
            db.add(adj_move)
            applied += 1

        db.flush()

        # Recalcular StockItem.qty y Product.stock para cada producto afectado
        affected_products = set(d["product_id"] for d in corrections_detail)
        for prod_id in affected_products:
            tenants = set(d["tenant_id"] for d in corrections_detail if d["product_id"] == prod_id)
            for tenant_id in tenants:
                # Recalcular qty total desde todos los moves
                total = (
                    db.query(func.coalesce(func.sum(StockMove.qty), 0.0))
                    .filter(
                        StockMove.product_id == prod_id,
                        StockMove.tenant_id == tenant_id,
                        StockMove.tentative == False,  # noqa: E712
                    )
                    .scalar()
                ) or 0.0

                # Actualizar todos los StockItems de ese producto
                stock_items = (
                    db.query(StockItem)
                    .filter(
                        StockItem.product_id == prod_id,
                        StockItem.tenant_id == tenant_id,
                    )
                    .all()
                )
                # Recalcular por warehouse
                for si in stock_items:
                    wh_total = (
                        db.query(func.coalesce(func.sum(StockMove.qty), 0.0))
                        .filter(
                            StockMove.product_id == prod_id,
                            StockMove.tenant_id == tenant_id,
                            StockMove.warehouse_id == si.warehouse_id,
                        )
                        .scalar()
                    ) or 0.0
                    si.qty = float(wh_total)

                # Actualizar products.stock (suma todos los warehouses)
                prod = db.query(Product).filter(
                    Product.id == prod_id, Product.tenant_id == tenant_id
                ).first()
                if prod:
                    prod.stock = float(total)

        db.commit()
        print(f"\nCorregidos {applied} stock_moves.")
        print("Stock de productos actualizado.")
        print("\nDone. Los valores ahora están en la unidad del producto (kg, lb, etc.).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corrección retroactiva de unidades de producción")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra cambios, no modifica BD")
    parser.add_argument("--tenant-id", help="Limitar a un tenant específico")
    args = parser.parse_args()

    run(dry_run=args.dry_run, tenant_filter=args.tenant_id)
