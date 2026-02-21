"""
Recipe Calculator - Servicio de cálculo de costos y producción
Calcula costos de recetas y materiales necesarios para producción
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.production._cost_drivers import ProductionCostDriver, RecipeCostLine
from app.models.recipes import Recipe, RecipeIngredient

# ============================================================================
# CÁLCULO DE COSTOS
# ============================================================================


def calculate_recipe_cost(db: Session, recipe_id: UUID, update_product_price: bool = True) -> dict:
    """
    Calcula costo total de receta con desglose detallado

    Args:
        db: Sesión de base de datos
        recipe_id: ID de la receta
        update_product_price: Si True, actualiza el precio sugerido del producto

    Returns:
        {
            "recipe_id": UUID,
            "name": str,
            "yield_qty": int,
            "total_cost": float,
            "unit_cost": float,
            "suggested_price": float,
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

    # Calcular precio sugerido con multiplicador óptimo basado en costo promedio
    unit_cost = float(recipe.unit_cost or 0)
    # Obtener costos unitarios de todas las recetas del tenant para calcular media
    all_costs = [
        float(r.unit_cost)
        for r in db.query(Recipe.unit_cost).filter(Recipe.unit_cost.isnot(None), Recipe.unit_cost > 0).all()
    ]
    if all_costs:
        avg_cost = sum(all_costs) / len(all_costs)
        # Curva continua: food cost target 25%-35% según nivel de costo promedio
        target_food_cost = 0.25 + 0.10 * min(1.0, avg_cost / 20.0)
        optimal_multiplier = round(1.0 / target_food_cost, 2)
    else:
        optimal_multiplier = 2.0  # fallback
    suggested_price = round(unit_cost * optimal_multiplier, 2)

    # Actualizar producto si está asociado y se solicita
    if update_product_price and recipe.product_id:
        product = db.query(Product).filter(Product.id == recipe.product_id).first()
        if product:
            product.suggested_price = suggested_price
            # Actualizar precio si use_suggested_price está activo
            if product.use_suggested_price:
                product.price = suggested_price
            db.add(product)
            db.commit()
            db.refresh(product)

    return {
        "recipe_id": str(recipe.id),
        "name": recipe.name,
        "yield_qty": recipe.yield_qty,
        "total_cost": round(float(costo_total), 2),
        "unit_cost": unit_cost,
        "suggested_price": suggested_price,
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


def calculate_recipe_full_cost(db: Session, recipe_id: UUID) -> dict:
    """
    Calcula costo completo de receta: materiales + costos indirectos.

    Returns:
        {
            "recipe_id", "recipe_name", "yield_qty",
            "materials_total", "materials_unit",
            "labor_total", "energy_total", "other_indirect_total",
            "indirect_total",
            "full_cost_total", "full_cost_unit",
            "cost_lines": [...]
        }
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Receta no encontrada: {recipe_id}")

    # Materials cost (from existing calculator)
    materials_total = Decimal(str(recipe.total_cost or 0))
    yield_qty = max(recipe.yield_qty or 1, 1)
    materials_unit = materials_total / yield_qty

    # Indirect costs from recipe_cost_lines
    cost_lines = (
        db.query(RecipeCostLine)
        .filter(RecipeCostLine.recipe_id == recipe_id)
        .order_by(RecipeCostLine.line_order)
        .all()
    )

    labor_total = Decimal("0")
    other_total = Decimal("0")
    lines_detail = []

    for line in cost_lines:
        driver = line.driver
        if not driver:
            continue
        effective_rate = line.rate_override if line.rate_override is not None else driver.default_rate
        line_cost = Decimal(str(line.qty_standard)) * Decimal(str(effective_rate)) * Decimal(str(line.headcount))

        code_upper = (driver.code or "").upper()
        if code_upper.startswith("LABOR"):
            labor_total += line_cost
        else:
            other_total += line_cost

        lines_detail.append({
            "id": str(line.id),
            "recipe_id": str(line.recipe_id),
            "driver_id": str(line.driver_id),
            "qty_standard": float(line.qty_standard),
            "headcount": line.headcount,
            "rate_override": float(line.rate_override) if line.rate_override is not None else None,
            "notes": line.notes,
            "line_order": line.line_order,
            "created_at": line.created_at.isoformat() if line.created_at else None,
            "driver_code": driver.code,
            "driver_name": driver.name,
            "driver_unit": driver.unit,
            "driver_default_rate": float(driver.default_rate),
            "effective_rate": float(effective_rate),
            "line_cost": round(float(line_cost), 4),
        })

    # Energy: auto-calculated from recipe baking_time_minutes × oven driver rate
    energy_total = Decimal("0")
    baking_minutes = getattr(recipe, "baking_time_minutes", None) or 0
    if baking_minutes > 0:
        # Find oven/energy driver for this tenant
        oven_driver = (
            db.query(ProductionCostDriver)
            .filter(
                ProductionCostDriver.tenant_id == recipe.tenant_id,
                ProductionCostDriver.is_active.is_(True),
                ProductionCostDriver.code.ilike("ENERGY%") | ProductionCostDriver.code.ilike("OVEN%"),
            )
            .first()
        )
        if oven_driver:
            oven_rate = Decimal(str(oven_driver.default_rate or 0))
            baking_hours = Decimal(str(baking_minutes)) / Decimal("60")
            energy_total = baking_hours * oven_rate
            lines_detail.append({
                "id": None,
                "recipe_id": str(recipe.id),
                "driver_id": str(oven_driver.id),
                "qty_standard": round(float(baking_hours), 4),
                "headcount": 1,
                "rate_override": None,
                "notes": f"Auto: {baking_minutes} min horneado",
                "line_order": 999,
                "created_at": None,
                "driver_code": oven_driver.code,
                "driver_name": oven_driver.name,
                "driver_unit": oven_driver.unit,
                "driver_default_rate": float(oven_driver.default_rate),
                "effective_rate": float(oven_rate),
                "line_cost": round(float(energy_total), 4),
                "_auto": True,
            })

    # Tray info for reference
    trays = getattr(recipe, "trays_per_batch", None)
    units_tray = getattr(recipe, "units_per_tray", None)

    indirect_total = labor_total + energy_total + other_total
    full_cost_total = materials_total + indirect_total
    full_cost_unit = full_cost_total / yield_qty

    return {
        "recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "yield_qty": yield_qty,
        "materials_total": round(float(materials_total), 4),
        "materials_unit": round(float(materials_unit), 4),
        "labor_total": round(float(labor_total), 4),
        "energy_total": round(float(energy_total), 4),
        "other_indirect_total": round(float(other_total), 4),
        "indirect_total": round(float(indirect_total), 4),
        "full_cost_total": round(float(full_cost_total), 4),
        "full_cost_unit": round(float(full_cost_unit), 4),
        "baking_time_minutes": baking_minutes,
        "trays_per_batch": trays,
        "units_per_tray": units_tray,
        "cost_lines": lines_detail,
    }


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
    prep = recipe.prep_time_minutes or 0
    baking = getattr(recipe, "baking_time_minutes", None) or 0
    rest = getattr(recipe, "rest_time_minutes", None) or 0
    tiempo_por_batch = prep + baking + rest
    tiempo_total = int(batches * tiempo_por_batch)

    # Ajustar por número de trabajadores (simplificado)
    tiempo_con_workers = tiempo_total / workers if workers > 0 else tiempo_total

    return {
        "batches": round(batches, 2),
        "tiempo_por_batch_min": tiempo_por_batch,
        "prep_time_min": prep,
        "baking_time_min": baking,
        "rest_time_min": rest,
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

  