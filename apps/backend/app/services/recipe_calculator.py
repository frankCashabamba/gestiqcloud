"""
Recipe Calculator - Servicio de cálculo de costos y producción
Calcula costos de recetas y materiales necesarios para producción
"""

from decimal import Decimal
from uuid import UUID

from app.models.core.products import Product
from app.models.recipes import Recipe, RecipeIngredient
from sqlalchemy import text
from sqlalchemy.orm import Session

# ============================================================================
# CÁLCULO DE COSTOS
# ============================================================================


def calculate_recipe_cost(db: Session, recipe_id: UUID) -> dict:
    """
    Calcula costo total de receta con desglose detallado

    Returns:
        {
            "recipe_id": UUID,
            "name": str,
            "yield_qty": int,
            "total_cost": float,
            "unit_cost": float,
            "ingredients_count": int,
            "breakdown": [
                {
                    "product": str,
                    "qty": float,
                    "unit": str,
                    "cost": float,
                    "percentage": float
                }
            ]
        }
    """
    # Obtener receta
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not recipe:
        raise ValueError(f"Receta no encontrada: {recipe_id}")

    # Obtener ingredientes
    ingredientes = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).all()

    # Calcular costo total sumando todos los ingredientes
    # Los costos individuales ya están calculados por la columna GENERATED
    desglose = []
    costo_total = Decimal("0")

    for ing in ingredientes:
        producto = db.query(Product).filter(Product.id == ing.product_id).first()

        # costo_ingrediente ya está calculado por la columna GENERATED
        costo_ing = Decimal(str(ing.ingredient_cost or 0))
        costo_total += costo_ing

        desglose.append(
            {
                "product_id": str(ing.product_id),
                "product": producto.name if producto else "Unknown",
                "qty": float(ing.qty),
                "unit": ing.unit,
                "purchase_packaging": ing.purchase_packaging,
                "cost": round(float(costo_ing), 4),
                "percentage": 0,  # Calculated later
            }
        )

    # Calcular porcentajes
    costo_total_float = float(costo_total)
    for item in desglose:
        item["percentage"] = (
            (item["cost"] / costo_total_float * 100) if costo_total_float > 0 else 0
        )

    # Actualizar solo costo_total (costo_por_unidad se calcula automáticamente)
    recipe.total_cost = costo_total

    db.commit()
    db.refresh(recipe)

    return {
        "recipe_id": str(recipe.id),
        "name": recipe.name,
        "yield_qty": recipe.yield_qty,
        "total_cost": round(float(costo_total), 2),
        "unit_cost": round(float(recipe.unit_cost or 0), 4),
        "ingredients_count": len(ingredientes),
        "breakdown": sorted(desglose, key=lambda x: x["cost"], reverse=True),
    }


def calculate_ingredient_cost(
    qty: float, unit: str, qty_per_package: float, package_cost: float
) -> float:
    """
    Calcula costo de ingrediente basado en presentación de compra

    Args:
        qty: Cantidad usada en receta
        unit: Unidad de medida
        qty_per_package: Cantidad en presentación (ej. 110 lb)
        package_cost: Costo de presentación (ej. $35)

    Returns:
        Costo del ingrediente usado

    Ejemplo:
        calculate_ingredient_cost(50, "lb", 110, 35.00)
        -> 50 * (35 / 110) = $15.91
    """
    if qty_per_package <= 0:
        raise ValueError("Cantidad de presentación debe ser > 0")

    costo_unitario = package_cost / qty_per_package
    costo_ingrediente = qty * costo_unitario

    return round(costo_ingrediente, 4)


# ============================================================================
# CÁLCULO DE PRODUCCIÓN
# ============================================================================


def calculate_purchase_for_production(db: Session, recipe_id: UUID, qty_to_produce: int) -> dict:
    """
    Calcula materiales necesarios para producir X unidades

    Args:
        db: Sesión de base de datos
        recipe_id: ID de la receta
        qty_to_produce: Cantidad a producir

    Returns:
        {
            "recipe": {...},
            "qty_to_produce": int,
            "batches_required": float,
            "ingredientes": [
                {
                    "producto": str,
                    "qty_necesaria": float,
                    "unidad": str,
                    "presentaciones_necesarias": int,
                    "presentacion_compra": str,
                    "costo_estimado": float
                }
            ],
            "costo_total_produccion": float,
            "costo_por_unidad": float
        }
    """
    # Verificar receta
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Receta no encontrada: {recipe_id}")

    # Calcular batches
    batches_required = qty_to_produce / recipe.yield_qty

    # Usar función PostgreSQL
    result = db.execute(
        text("SELECT * FROM calculate_production_materials(:recipe_id, :qty)"),
        {"recipe_id": str(recipe_id), "qty": qty_to_produce},
    ).fetchall()

    ingredientes = []
    costo_total = 0.0

    for row in result:
        ingredientes.append(
            {
                "product_id": str(row.producto_id),
                "product": row.producto_nombre,
                "required_qty": float(row.qty_necesaria),
                "unit": row.unidad_medida,
                "packages_required": int(row.presentaciones_necesarias),
                "purchase_packaging": row.presentacion_compra,
                "estimated_cost": float(row.costo_estimado),
            }
        )
        costo_total += float(row.costo_estimado)

    return {
        "recipe": {
            "id": str(recipe.id),
            "name": recipe.name,
            "yield_qty": recipe.yield_qty,
        },
        "qty_to_produce": qty_to_produce,
        "batches_required": round(batches_required, 2),
        "ingredients": ingredientes,
        "total_production_cost": round(costo_total, 2),
        "unit_cost": round(costo_total / qty_to_produce, 4) if qty_to_produce > 0 else 0,
    }


def calculate_production_time(
    db: Session, recipe_id: UUID, qty_to_produce: int, workers: int = 1
) -> dict:
    """
    Estima tiempo de producción

    Args:
        recipe_id: ID de receta
        qty_to_produce: Cantidad a producir
        workers: Número de trabajadores

    Returns:
        {
            "batches": float,
            "tiempo_por_batch_min": int,
            "tiempo_total_min": int,
            "tiempo_total_horas": float,
            "workers": int
        }
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Receta no encontrada: {recipe_id}")

    batches = qty_to_produce / recipe.yield_qty
    tiempo_por_batch = recipe.prep_time_minutes or 0
    tiempo_total = int(batches * tiempo_por_batch)

    # Ajustar por número de trabajadores (simplificado)
    tiempo_con_workers = tiempo_total / workers if workers > 0 else tiempo_total

    return {
        "batches": round(batches, 2),
        "tiempo_por_batch_min": tiempo_por_batch,
        "tiempo_total_min": int(tiempo_con_workers),
        "tiempo_total_horas": round(tiempo_con_workers / 60, 2),
        "workers": workers,
    }


# ============================================================================
# CREACIÓN DE ÓRDENES DE COMPRA
# ============================================================================


def create_purchase_order_from_recipe(
    db: Session,
    recipe_id: UUID,
    qty_to_produce: int,
    supplier_id: UUID | None = None,
) -> dict:
    """
    Crea orden de compra automática basada en receta

    Args:
        db: Sesión DB
        recipe_id: ID receta
        qty_to_produce: Cantidad a producir
        supplier_id: provider (opcional)

    Returns:
        Resumen de orden de compra

    Note:
        Esta función prepara datos para crear una orden de compra
        La integración con módulo de compras se hace en el router
    """
    calculation = calculate_purchase_for_production(db, recipe_id, qty_to_produce)

    # Preparar líneas de orden de compra
    purchase_lines = []
    for ing in calculation["ingredients"]:
        purchase_lines.append(
            {
                "product_id": ing["product_id"],
                "product_name": ing["product"],
                "qty": ing["packages_required"],
                "unit": "package",  # Comprar por presentación completa
                "precio_estimado": (
                    ing["estimated_cost"] / ing["packages_required"]
                    if ing["packages_required"] > 0
                    else 0
                ),
                "total": ing["estimated_cost"],
                "notes": f"To produce {qty_to_produce} {calculation['recipe']['name']}",
            }
        )

    return {
        "recipe_id": str(recipe_id),
        "recipe_name": calculation["recipe"]["name"],
        "qty_to_produce": qty_to_produce,
        "supplier_id": str(supplier_id) if supplier_id else None,
        "estimated_total": calculation["total_production_cost"],
        "lines": purchase_lines,
        "metadata": {
            "batches_required": calculation["batches_required"],
            "created_from": "recipe_calculator",
        },
    }


# ============================================================================
# ANÁLISIS Y COMPARACIONES
# ============================================================================


def compare_recipe_costs(db: Session, recipe_ids: list[UUID]) -> list[dict]:
    """
    Compara costos de múltiples recetas

    Returns:
        Lista ordenada por costo por unidad
    """
    comparisons = []

    for recipe_id in recipe_ids:
        try:
            cost_data = calculate_recipe_cost(db, recipe_id)
            recipe_name = cost_data.get("name") or cost_data.get("nombre")
            comparisons.append(
                {
                    "recipe_id": cost_data["recipe_id"],
                    "name": recipe_name,
                    "unit_cost": cost_data["unit_cost"],
                    "yield_qty": cost_data["yield_qty"],
                    "ingredients_count": cost_data["ingredients_count"],
                }
            )
        except Exception:
            continue

    # Ordenar por costo por unidad
    return sorted(comparisons, key=lambda x: x["unit_cost"])


def get_recipe_profitability(
    db: Session, recipe_id: UUID, selling_price: float, indirect_costs_pct: float = 0.30
) -> dict:
    """
    Calcula rentabilidad de receta

    Args:
        recipe_id: ID receta
        selling_price: Precio de venta por unidad
        indirect_costs_pct: % de costos indirectos (default 30%)

    Returns:
        {
            "direct_cost": float,
            "indirect_cost": float,
            "total_cost": float,
            "selling_price": float,
            "profit": float,
            "margin_percentage": float,
            "breakeven_units": int
        }
    """
    cost_data = calculate_recipe_cost(db, recipe_id)

    direct_cost = cost_data["unit_cost"]
    indirect_cost = direct_cost * indirect_costs_pct
    total_cost = direct_cost + indirect_cost
    profit = selling_price - total_cost
    margin = (profit / selling_price * 100) if selling_price > 0 else 0

    # Punto de equilibrio (asumiendo costos fijos)
    # Simplificado: si margen > 0, punto equilibrio = 1 unidad
    breakeven_units = 1 if profit > 0 else 0

    return {
        "recipe_id": str(recipe_id),
        "name": cost_data["name"],
        "direct_cost": round(direct_cost, 4),
        "indirect_cost": round(indirect_cost, 4),
        "total_cost": round(total_cost, 4),
        "selling_price": round(selling_price, 2),
        "profit": round(profit, 4),
        "margin_percentage": round(margin, 2),
        "breakeven_units": breakeven_units,
    }
