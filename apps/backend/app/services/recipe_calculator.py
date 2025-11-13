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
            "rendimiento": int,
            "costo_total": float,
            "costo_por_unidad": float,
            "ingredientes_count": int,
            "desglose": [
                {
                    "producto": str,
                    "qty": float,
                    "unidad": str,
                    "costo": float,
                    "porcentaje": float
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
        producto = db.query(Product).filter(Product.id == ing.producto_id).first()

        # costo_ingrediente ya está calculado por la columna GENERATED
        costo_ing = Decimal(str(ing.costo_ingrediente or 0))
        costo_total += costo_ing

        desglose.append(
            {
                "producto_id": str(ing.producto_id),
                "producto": producto.name if producto else "Desconocido",
                "qty": float(ing.qty),
                "unidad": ing.unidad_medida,
                "presentacion_compra": ing.presentacion_compra,
                "costo": round(float(costo_ing), 4),
                "porcentaje": 0,  # Se calculará después
            }
        )

    # Calcular porcentajes
    costo_total_float = float(costo_total)
    for item in desglose:
        item["porcentaje"] = (
            (item["costo"] / costo_total_float * 100) if costo_total_float > 0 else 0
        )

    # Actualizar solo costo_total (costo_por_unidad se calcula automáticamente)
    recipe.costo_total = costo_total

    db.commit()
    db.refresh(recipe)

    return {
        "recipe_id": str(recipe.id),
        "name": recipe.name,
        "rendimiento": recipe.rendimiento,
        "costo_total": round(float(costo_total), 2),
        "costo_por_unidad": round(float(recipe.costo_por_unidad), 4),
        "ingredientes_count": len(ingredientes),
        "desglose": sorted(desglose, key=lambda x: x["costo"], reverse=True),
    }


def calculate_ingredient_cost(
    qty: float, unidad: str, qty_presentacion: float, costo_presentacion: float
) -> float:
    """
    Calcula costo de ingrediente basado en presentación de compra

    Args:
        qty: Cantidad usada en receta
        unidad: Unidad de medida
        qty_presentacion: Cantidad en presentación (ej. 110 lb)
        costo_presentacion: Costo de presentación (ej. $35)

    Returns:
        Costo del ingrediente usado

    Ejemplo:
        calculate_ingredient_cost(50, "lb", 110, 35.00)
        -> 50 * (35 / 110) = $15.91
    """
    if qty_presentacion <= 0:
        raise ValueError("Cantidad de presentación debe ser > 0")

    costo_unitario = costo_presentacion / qty_presentacion
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
    batches_required = qty_to_produce / recipe.rendimiento

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
                "producto_id": str(row.producto_id),
                "producto": row.producto_nombre,
                "qty_necesaria": float(row.qty_necesaria),
                "unidad": row.unidad_medida,
                "presentaciones_necesarias": int(row.presentaciones_necesarias),
                "presentacion_compra": row.presentacion_compra,
                "costo_estimado": float(row.costo_estimado),
            }
        )
        costo_total += float(row.costo_estimado)

    return {
        "recipe": {
            "id": str(recipe.id),
            "nombre": recipe.name,
            "rendimiento": recipe.rendimiento,
        },
        "qty_to_produce": qty_to_produce,
        "batches_required": round(batches_required, 2),
        "ingredientes": ingredientes,
        "costo_total_produccion": round(costo_total, 2),
        "costo_por_unidad": round(costo_total / qty_to_produce, 4) if qty_to_produce > 0 else 0,
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

    batches = qty_to_produce / recipe.rendimiento
    tiempo_por_batch = recipe.tiempo_preparacion or 0
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
        supplier_id: Proveedor (opcional)

    Returns:
        Resumen de orden de compra

    Note:
        Esta función prepara datos para crear una orden de compra
        La integración con módulo de compras se hace en el router
    """
    calculation = calculate_purchase_for_production(db, recipe_id, qty_to_produce)

    # Preparar líneas de orden de compra
    purchase_lines = []
    for ing in calculation["ingredientes"]:
        purchase_lines.append(
            {
                "producto_id": ing["producto_id"],
                "producto_nombre": ing["producto"],
                "qty": ing["presentaciones_necesarias"],
                "unidad": "presentacion",  # Comprar por presentación completa
                "precio_estimado": (
                    ing["costo_estimado"] / ing["presentaciones_necesarias"]
                    if ing["presentaciones_necesarias"] > 0
                    else 0
                ),
                "total": ing["costo_estimado"],
                "notas": f"Para producción de {qty_to_produce} {calculation['recipe']['nombre']}",
            }
        )

    return {
        "recipe_id": str(recipe_id),
        "recipe_nombre": calculation["recipe"]["nombre"],
        "qty_to_produce": qty_to_produce,
        "supplier_id": str(supplier_id) if supplier_id else None,
        "total_estimado": calculation["costo_total_produccion"],
        "lineas": purchase_lines,
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
                    # compatibilidad con usos antiguos
                    "nombre": recipe_name,
                    "costo_por_unidad": cost_data["costo_por_unidad"],
                    "rendimiento": cost_data["rendimiento"],
                    "ingredientes_count": cost_data["ingredientes_count"],
                }
            )
        except Exception:
            continue

    # Ordenar por costo por unidad
    return sorted(comparisons, key=lambda x: x["costo_por_unidad"])


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
            "costo_directo": float,
            "costo_indirecto": float,
            "costo_total": float,
            "precio_venta": float,
            "ganancia": float,
            "margen_porcentaje": float,
            "punto_equilibrio_unidades": int
        }
    """
    cost_data = calculate_recipe_cost(db, recipe_id)

    costo_directo = cost_data["costo_por_unidad"]
    costo_indirecto = costo_directo * indirect_costs_pct
    costo_total = costo_directo + costo_indirecto
    ganancia = selling_price - costo_total
    margen = (ganancia / selling_price * 100) if selling_price > 0 else 0

    # Punto de equilibrio (asumiendo costos fijos)
    # Simplificado: si margen > 0, punto equilibrio = 1 unidad
    punto_equilibrio = 1 if ganancia > 0 else 0

    return {
        "recipe_id": str(recipe_id),
        "nombre": cost_data["nombre"],
        "costo_directo": round(costo_directo, 4),
        "costo_indirecto": round(costo_indirecto, 4),
        "costo_total": round(costo_total, 4),
        "precio_venta": round(selling_price, 2),
        "ganancia": round(ganancia, 4),
        "margen_porcentaje": round(margen, 2),
        "punto_equilibrio_unidades": punto_equilibrio,
    }
