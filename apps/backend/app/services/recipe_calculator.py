"""
Recipe Calculator - Servicio de cálculo de costos y producción
Calcula costos de recetas y materiales necesarios para producción
"""

import math
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings
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

    # Calcular precio sugerido usando multiplicador configurado por el tenant
    unit_cost = float(recipe.unit_cost or 0)

    # Leer multiplicador (% utilidad) desde CompanySettings del tenant
    optimal_multiplier = 1.25  # default: 25% utilidad
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == recipe.tenant_id).first()
    )
    if company_settings and company_settings.settings:
        saved = company_settings.settings.get("produccion_margin_multiplier")
        if saved is not None:
            optimal_multiplier = float(saved)

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


def calculate_recipe_full_cost(
    db: Session, recipe_id: UUID, period_month: str | None = None
) -> dict:
    """
    Calcula costo completo de receta: materiales + costos indirectos.

    Si period_month se proporciona, usa los datos reales del período.
    Si no, usa fórmulas simplificadas.

    Args:
        db: Sesión DB
        recipe_id: ID de receta
        period_month: Período en formato YYYY-MM para buscar CostPeriod (opcional)

    Returns:
        {
            "recipe_id", "recipe_name", "yield_qty",
            "materials_total", "materials_unit",
            "labor_total", "labor_burden_total",
            "diesel_total", "electricity_total",
            "indirect_total",
            "full_cost_total", "full_cost_unit",
            "cost_lines": [...],
            "breakdown": {
                "materials": float,
                "labor": float,
                "diesel": float,
                "electricity": float,
                "other": float
            }
        }
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Receta no encontrada: {recipe_id}")

    # Materials cost (from existing calculator)
    materials_total = Decimal(str(recipe.total_cost or 0))
    yield_qty = max(recipe.yield_qty or 1, 1)
    materials_unit = materials_total / yield_qty

    # Obtener CostPeriod si existe
    cost_period = None
    from app.models.production._cost_periods import CostPeriod

    if period_month:
        cost_period = (
            db.query(CostPeriod)
            .filter(
                CostPeriod.month == period_month,
                CostPeriod.tenant_id == recipe.tenant_id,
                CostPeriod.is_active,
            )
            .first()
        )
    if not cost_period:
        # Auto: usar el período activo más reciente del tenant
        cost_period = (
            db.query(CostPeriod)
            .filter(CostPeriod.tenant_id == recipe.tenant_id, CostPeriod.is_active)
            .order_by(CostPeriod.month.desc())
            .first()
        )

    # Indirect costs from recipe_cost_lines
    cost_lines = (
        db.query(RecipeCostLine)
        .filter(RecipeCostLine.recipe_id == recipe_id)
        .order_by(RecipeCostLine.line_order)
        .all()
    )

    labor_total = Decimal("0")
    diesel_total = Decimal("0")
    electricity_total = Decimal("0")
    other_total = Decimal("0")
    lines_detail = []

    # ========== CÁLCULO DE TIEMPO DE TRABAJO ==========
    # Usar touch_minutes_standard si está definido, sino calcular de prep/baking/rest
    touch_minutes = recipe.touch_minutes_standard or 0
    oven_minutes = recipe.oven_minutes_standard or 0

    if touch_minutes == 0:
        # Fallback: calcular de los campos legacy
        prep_mins = getattr(recipe, "prep_time_minutes", None) or 0
        baking_mins = getattr(recipe, "baking_time_minutes", None) or 0
        rest_mins = getattr(recipe, "rest_time_minutes", None) or 0
        touch_minutes = max(prep_mins - baking_mins - rest_mins, 0)

    if touch_minutes == 0:
        from app.models.production._recipe_steps import RecipeStep

        steps = (
            db.query(RecipeStep)
            .filter(
                RecipeStep.recipe_id == recipe_id,
                RecipeStep.is_active,
            )
            .all()
        )
        if steps:
            touch_minutes = sum(s.duration_minutes or 0 for s in steps if s.is_touch)
            oven_from_steps = sum(
                s.duration_minutes or 0 for s in steps if s.resource_type == "oven"
            )
            if oven_from_steps > 0 and oven_minutes == 0:
                oven_minutes = oven_from_steps

    if oven_minutes == 0:
        oven_minutes = getattr(recipe, "baking_time_minutes", None) or 0

    touch_hours = Decimal(str(touch_minutes)) / Decimal("60")
    oven_hours = Decimal(str(oven_minutes)) / Decimal("60")

    # ========== PROCESAMIENTO DE LÍNEAS DE COSTO ==========
    for line in cost_lines:
        driver = line.driver
        if not driver:
            continue
        effective_rate = (
            line.rate_override if line.rate_override is not None else driver.default_rate
        )
        code_upper = (driver.code or "").upper()

        # Clasificar tipo de costo
        is_labor = code_upper.startswith("LABOR") or (
            (driver.unit or "").lower() == "hour"
            and not code_upper.startswith("ENERGY")
            and not code_upper.startswith("DIESEL")
            and not code_upper.startswith("OVEN")
        )
        is_diesel = code_upper.startswith("DIESEL") or code_upper.startswith("FUEL")
        is_electricity = code_upper.startswith("ENERGY") or code_upper.startswith("ELECTRICITY")

        # Determinar cantidad a usar
        qty = Decimal(str(line.qty_standard))

        # Para labor: usar touch_hours o qty_standard
        if is_labor and touch_hours > 0:
            qty = touch_hours

        # Para diésel: usar oven_hours si CostPeriod existe
        if is_diesel and cost_period and oven_hours > 0:
            qty = oven_hours

        # Para electricidad: usar touch_hours si CostPeriod existe
        if is_electricity and cost_period and touch_hours > 0:
            qty = touch_hours

        line_cost = qty * Decimal(str(effective_rate)) * Decimal(str(line.headcount))

        # Categorizar costo
        if is_labor:
            labor_total += line_cost
        elif is_diesel:
            diesel_total += line_cost
        elif is_electricity:
            electricity_total += line_cost
        else:
            other_total += line_cost

        lines_detail.append(
            {
                "id": str(line.id),
                "recipe_id": str(line.recipe_id),
                "driver_id": str(line.driver_id),
                "qty_standard": round(float(qty), 4),
                "headcount": line.headcount,
                "rate_override": (
                    float(line.rate_override) if line.rate_override is not None else None
                ),
                "notes": line.notes,
                "line_order": line.line_order,
                "created_at": line.created_at.isoformat() if line.created_at else None,
                "driver_code": driver.code,
                "driver_name": driver.name,
                "driver_unit": driver.unit,
                "driver_default_rate": float(driver.default_rate),
                "effective_rate": float(effective_rate),
                "line_cost": round(float(line_cost), 4),
                "cost_category": (
                    "labor"
                    if is_labor
                    else ("diesel" if is_diesel else ("electricity" if is_electricity else "other"))
                ),
                "_auto": True,
            }
        )

    # Auto-calculate from CostPeriod when no cost lines cover these categories
    if cost_period:
        # Labor: auto si no hay cost lines de labor
        if labor_total == 0 and touch_hours > 0 and cost_period.labor_hour_rate:
            labor_total = touch_hours * Decimal(str(cost_period.labor_hour_rate))

        # Diesel: auto si no hay cost lines de diesel
        if diesel_total == 0 and oven_hours > 0 and cost_period.diesel_per_oven_hour:
            diesel_total = oven_hours * Decimal(str(cost_period.diesel_per_oven_hour))

        # Electricidad: auto si no hay cost lines de electricidad
        if electricity_total == 0 and touch_hours > 0 and cost_period.electricity_per_hour:
            electricity_total = touch_hours * Decimal(str(cost_period.electricity_per_hour))

    # ========== APLICAR BURDEN FACTOR Y COSTOS DEL PERÍODO ==========
    # Si existe CostPeriod, aplicar burden factor a labor
    labor_burden_factor = Decimal("1.0")
    if cost_period and cost_period.labor_burden_factor:
        labor_burden_factor = Decimal(str(cost_period.labor_burden_factor))

    # Si CostPeriod existe, usar sus rates en lugar de defaults
    if cost_period:
        # Actualizar diésel usando diesel_per_oven_hour del período
        if cost_period.diesel_per_oven_hour and oven_hours > 0:
            diesel_total = oven_hours * Decimal(str(cost_period.diesel_per_oven_hour))

        # Actualizar electricidad usando electricity_per_hour del período
        if cost_period.electricity_per_hour and touch_hours > 0:
            electricity_total = touch_hours * Decimal(str(cost_period.electricity_per_hour))

    # ========== ENERGY/OVEN: si no está en cost_period ==========
    # Energy: auto-calculated from recipe oven_time × oven driver rate (fallback si no hay period)
    if not cost_period:
        baking_minutes = oven_minutes or 0
        if baking_minutes > 0:
            # Find oven/energy driver for this tenant
            oven_driver = (
                db.query(ProductionCostDriver)
                .filter(
                    ProductionCostDriver.tenant_id == recipe.tenant_id,
                    ProductionCostDriver.is_active.is_(True),
                    ProductionCostDriver.code.ilike("ENERGY%")
                    | ProductionCostDriver.code.ilike("OVEN%"),
                )
                .first()
            )
            if oven_driver:
                oven_rate = Decimal(str(oven_driver.default_rate or 0))
                baking_hours = Decimal(str(baking_minutes)) / Decimal("60")
                electricity_total = baking_hours * oven_rate
                lines_detail.append(
                    {
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
                        "line_cost": round(float(electricity_total), 4),
                        "_auto": True,
                    }
                )

    # Aplicar burden factor al labor total
    labor_with_burden = labor_total * labor_burden_factor

    # Tray info for reference
    trays = getattr(recipe, "trays_per_batch", None)
    units_tray = getattr(recipe, "units_per_tray", None)

    # Totales indirectos
    indirect_total = labor_with_burden + diesel_total + electricity_total + other_total
    full_cost_total = materials_total + indirect_total
    full_cost_unit = full_cost_total / yield_qty if yield_qty > 0 else Decimal("0")

    return {
        "recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "yield_qty": yield_qty,
        "period_month": cost_period.month if cost_period else period_month,
        "period_id": str(cost_period.id) if cost_period else None,
        "materials_total": round(float(materials_total), 4),
        "materials_unit": round(float(materials_unit), 4),
        "labor_total": round(float(labor_total), 4),
        "labor_with_burden_factor": round(float(labor_with_burden), 4),
        "labor_burden_factor": round(float(labor_burden_factor), 4),
        "diesel_total": round(float(diesel_total), 4),
        "electricity_total": round(float(electricity_total), 4),
        "other_indirect_total": round(float(other_total), 4),
        "indirect_total": round(float(indirect_total), 4),
        "full_cost_total": round(float(full_cost_total), 4),
        "full_cost_unit": round(float(full_cost_unit), 4),
        "touch_minutes": touch_minutes,
        "oven_minutes": oven_minutes,
        "trays_per_batch": trays,
        "units_per_tray": units_tray,
        "breakdown": {
            "materials": round(float(materials_total), 4),
            "labor": round(float(labor_with_burden), 4),
            "diesel": round(float(diesel_total), 4),
            "electricity": round(float(electricity_total), 4),
            "other": round(float(other_total), 4),
        },
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

    ingredientes_receta = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .order_by(RecipeIngredient.line_order.asc(), RecipeIngredient.created_at.asc())
        .all()
    )

    # Calcular batches
    yield_qty = Decimal(str(recipe.yield_qty or 0))
    if yield_qty <= 0:
        raise ValueError(f"Receta con rendimiento inválido: {recipe_id}")
    batches_required = Decimal(str(qty_to_produce)) / yield_qty

    ingredientes = []
    costo_total = Decimal("0")

    for ing in ingredientes_receta:
        qty_base = Decimal(str(ing.qty or 0))
        qty_per_package = Decimal(str(ing.qty_per_package or 0))
        package_cost = Decimal(str(ing.package_cost or 0))

        if qty_base <= 0:
            continue

        required_qty = (qty_base * batches_required).quantize(Decimal("0.0001"))
        if required_qty <= 0:
            continue

        packages_required = 0
        if qty_per_package > 0:
            packages_required = math.ceil(float(required_qty / qty_per_package))

        # Costo proporcional (consumo real), no redondeado a paquetes enteros
        if qty_per_package > 0 and package_cost > 0:
            estimated_cost = (required_qty * package_cost / qty_per_package).quantize(
                Decimal("0.0001")
            )
        elif qty_per_package <= 0:
            ingredient_cost = Decimal(str(getattr(ing, "ingredient_cost", 0) or 0))
            unit_cost = (
                (ingredient_cost / qty_base)
                if qty_base > 0 and ingredient_cost > 0
                else Decimal("0")
            )
            estimated_cost = (required_qty * unit_cost).quantize(Decimal("0.0001"))
        else:
            estimated_cost = Decimal("0")

        product = db.query(Product).filter(Product.id == ing.product_id).first()
        package_label = ing.purchase_packaging or (
            f"{float(qty_per_package):g} {ing.package_unit}"
            if qty_per_package > 0 and ing.package_unit
            else "-"
        )

        ingredientes.append(
            {
                "producto_id": str(ing.product_id),
                "producto": product.name if product else "Unknown",
                "qty_necesaria": round(float(required_qty), 4),
                "unidad": ing.unit,
                "presentaciones_necesarias": packages_required,
                "presentacion_compra": package_label,
                "costo_estimado": round(float(estimated_cost), 4),
            }
        )
        costo_total += estimated_cost

    return {
        "recipe": {
            "id": str(recipe.id),
            "name": recipe.name,
            "rendimiento": recipe.yield_qty,
        },
        "qty_to_produce": qty_to_produce,
        "batches_required": round(float(batches_required), 2),
        "ingredientes": ingredientes,
        "costo_total_produccion": round(float(costo_total), 2),
        "costo_por_unidad": (
            round(float(costo_total / Decimal(str(qty_to_produce))), 4) if qty_to_produce > 0 else 0
        ),
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
    for ing in calculation["ingredientes"]:
        purchase_lines.append(
            {
                "product_id": ing["producto_id"],
                "product_name": ing["producto"],
                "qty": ing["presentaciones_necesarias"],
                "unit": "package",  # Comprar por presentación completa
                "precio_estimado": (
                    ing["costo_estimado"] / ing["presentaciones_necesarias"]
                    if ing["presentaciones_necesarias"] > 0
                    else 0
                ),
                "total": ing["costo_estimado"],
                "notes": f"To produce {qty_to_produce} {calculation['recipe']['name']}",
            }
        )

    return {
        "recipe_id": str(recipe_id),
        "recipe_name": calculation["recipe"]["name"],
        "qty_to_produce": qty_to_produce,
        "supplier_id": str(supplier_id) if supplier_id else None,
        "estimated_total": calculation["costo_total_produccion"],
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
