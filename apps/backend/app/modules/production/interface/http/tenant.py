"""
Producción Module - HTTP API Tenant Interface

Sistema completo de planificación y ejecución de producción basado en recetas:
- CRUD de órdenes de producción
- Iniciar/Completar/Cancelar producción
- Consumo automático de stock (ingredientes)
- Generación automática de productos terminados
- Registro de mermas y desperdicios
- Calculadora de producción (planificación)
- Estadísticas y reportes
- Gestión de recetas y BOM

Compatible con: Panadería, Restaurante, y cualquier sector con recetas/BOM

MIGRADO DE:
- app/routers/production.py
- app/routers/recipes.py
"""

import logging
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.config.database import IS_SQLITE, PG_SCHEMA_NAME, get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls, tenant_id_guc_expr_text
from app.models.core.global_catalogs import UnitOfMeasure
from app.models.core.products import Product
from app.models.expenses.expense import Expense
from app.models.inventory.stock import StockItem, StockMove
from app.models.inventory.warehouse import Warehouse
from app.models.pos.receipt import POSReceipt, POSReceiptLine
from app.models.production._cost_drivers import (
    CostDriverUnitType,
    ProductionCostDriver,
    ProductionOrderCost,
    RecipeCostLine,
)
from app.models.production._cost_periods import CostPeriod
from app.models.production._recipe_steps import RecipeStep
from app.models.production.production_order import ProductionOrder, ProductionOrderLine
from app.models.recipes import Recipe, RecipeIngredient
from app.modules.feature_flags.dependencies import require_flag
from app.schemas.cost_periods import (
    CostPeriodCreate,
    CostPeriodResponse,
    CostPeriodSummary,
    CostPeriodUpdate,
    CostPeriodValidationResult,
)
from app.schemas.production import (
    IngredientRequirement,
    ProductionCalculatorRequest,
    ProductionCalculatorResponse,
    ProductionOrderCompleteRequest,
    ProductionOrderCreate,
    ProductionOrderList,
    ProductionOrderResponse,
    ProductionOrderStartRequest,
    ProductionOrderStats,
    ProductionOrderUpdate,
    ProductionPlanningSuggestion,
)
from app.schemas.production_costs import (
    CostDriverCreate,
    CostDriverResponse,
    CostDriverUpdate,
    OrderCostCreate,
    OrderCostResponse,
    RecipeCostLineCreate,
    RecipeCostLineResponse,
    RecipeCostLineUpdate,
    RecipeFullCostSummary,
)
from app.schemas.recipes import (
    ProductionCalculationRequest,
    ProductionCalculationResponse,
    PurchaseOrderRequest,
    PurchaseOrderResponse,
    RecipeComparisonResponse,
    RecipeCostBreakdownResponse,
    RecipeCreate,
    RecipeDetailResponse,
    RecipeIngredientCreate,
    RecipeIngredientResponse,
    RecipeIngredientUpdate,
    RecipeOptimizationRequest,
    RecipeOptimizationResponse,
    RecipeProfitabilityRequest,
    RecipeProfitabilityResponse,
    RecipeResponse,
    RecipeStepCreate,
    RecipeStepResponse,
    RecipeStepUpdate,
    RecipeUpdate,
)
from app.services.cost_periods_service import CostPeriodsService
from app.services.product_raw_materials import sync_product_as_raw_material_from_recipe_line
from app.services.recipe_calculator import (
    bulk_calculate_recipe_full_costs,
    calculate_production_time,
    calculate_purchase_for_production,
    calculate_recipe_cost,
    calculate_recipe_full_cost,
    compare_recipe_costs,
    create_purchase_order_from_recipe,
    get_recipe_profitability,
)
from app.services.recipe_optimizer import optimize_recipe_with_ai

router = APIRouter(
    prefix="/production",
    tags=["Production"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)
logger = logging.getLogger(__name__)


# HELPERS
def _normalize_cost_driver_unit_token(value: str | None) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def _list_cost_driver_unit_options(db: Session, tenant_id: UUID) -> list[object]:
    unit_types = (
        db.query(CostDriverUnitType)
        .filter(CostDriverUnitType.tenant_id == tenant_id, CostDriverUnitType.is_active)
        .order_by(CostDriverUnitType.sort_order, CostDriverUnitType.code)
        .all()
    )
    if unit_types:
        return unit_types

    return (
        db.query(UnitOfMeasure)
        .filter(UnitOfMeasure.active.is_(True))
        .order_by(UnitOfMeasure.code)
        .all()
    )


def _cost_driver_unit_option_code(unit_option: object) -> str:
    return str(getattr(unit_option, "code", "") or "").strip()


def _cost_driver_unit_option_name_en(unit_option: object) -> str:
    return str(
        getattr(unit_option, "name_en", None) or getattr(unit_option, "name", None) or ""
    ).strip()


def _cost_driver_unit_option_name_es(unit_option: object) -> str:
    return str(
        getattr(unit_option, "name_es", None) or getattr(unit_option, "name", None) or ""
    ).strip()


def _cost_driver_unit_option_abbreviation(unit_option: object) -> str:
    return str(getattr(unit_option, "abbreviation", "") or "").strip()


def _serialize_cost_driver_unit_option(unit_option: object) -> dict[str, object]:
    return {
        "id": str(getattr(unit_option, "id", "") or ""),
        "code": _cost_driver_unit_option_code(unit_option),
        "name_en": _cost_driver_unit_option_name_en(unit_option),
        "name_es": _cost_driver_unit_option_name_es(unit_option) or None,
        "is_active": bool(getattr(unit_option, "is_active", getattr(unit_option, "active", True))),
        "sort_order": int(getattr(unit_option, "sort_order", 0) or 0),
    }


def _cost_driver_unit_option_aliases(unit_option: object) -> set[str]:
    aliases = {
        _normalize_cost_driver_unit_token(_cost_driver_unit_option_code(unit_option)),
        _normalize_cost_driver_unit_token(_cost_driver_unit_option_name_en(unit_option)),
        _normalize_cost_driver_unit_token(_cost_driver_unit_option_name_es(unit_option)),
        _normalize_cost_driver_unit_token(_cost_driver_unit_option_abbreviation(unit_option)),
    }
    aliases.discard("")
    return aliases


def _resolve_cost_driver_unit_code(db: Session, tenant_id: UUID, raw_unit: str | None) -> str:
    unit = str(raw_unit or "").strip()
    if not unit:
        return unit

    unit_types = _list_cost_driver_unit_options(db, tenant_id)
    if not unit_types:
        return unit

    normalized_unit = _normalize_cost_driver_unit_token(unit)

    for unit_type in unit_types:
        if normalized_unit in _cost_driver_unit_option_aliases(unit_type):
            return _cost_driver_unit_option_code(unit_type)

    raise HTTPException(status_code=400, detail=f"Unidad de costo no válida: {unit}")


def _require_recipe_for_tenant(db: Session, tenant_id: UUID, recipe_id: UUID) -> Recipe:
    recipe = (
        db.execute(
            select(Recipe).where(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id)
        ).scalar_one_or_none()
    )
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
    return recipe


def _require_product_for_tenant(db: Session, tenant_id: UUID, product_id: UUID) -> Product:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.tenant_id == tenant_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")
    return product


def _require_warehouse_for_tenant(db: Session, tenant_id: UUID, warehouse_id: UUID) -> Warehouse:
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == warehouse_id, Warehouse.tenant_id == str(tenant_id))
        .first()
    )
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")
    return warehouse


def _ensure_order_costs_indexes_and_rls(db: Session) -> None:
    if IS_SQLITE:
        return

    full_table_name = f"{PG_SCHEMA_NAME}.production_order_costs"
    tenant_expr = tenant_id_guc_expr_text()
    inspector = inspect(db.bind)
    indexes = inspector.get_indexes("production_order_costs", schema=PG_SCHEMA_NAME)
    indexed_columns = {tuple(index.get("column_names") or []) for index in indexes}

    if ("order_id",) not in indexed_columns:
        db.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS idx_prod_order_costs_order
                ON {full_table_name} (order_id)
                """
            )
        )
    if ("driver_id",) not in indexed_columns:
        db.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS idx_prod_order_costs_driver
                ON {full_table_name} (driver_id)
                """
            )
        )
    db.execute(text(f"ALTER TABLE {full_table_name} ENABLE ROW LEVEL SECURITY"))
    db.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname = '{PG_SCHEMA_NAME}'
                      AND tablename = 'production_order_costs'
                      AND policyname = 'production_order_costs_tenant_policy'
                ) THEN
                    CREATE POLICY production_order_costs_tenant_policy
                    ON {full_table_name}
                    USING (
                        EXISTS (
                            SELECT 1
                            FROM {PG_SCHEMA_NAME}.production_orders po
                            WHERE po.id = order_id
                              AND po.tenant_id = {tenant_expr}
                        )
                    )
                    WITH CHECK (
                        EXISTS (
                            SELECT 1
                            FROM {PG_SCHEMA_NAME}.production_orders po
                            WHERE po.id = order_id
                              AND po.tenant_id = {tenant_expr}
                        )
                    );
                END IF;
            END
            $$;
            """
        )
    )


def _order_costs_storage_available(db: Session) -> bool:
    cached = db.info.get("production_order_costs_available")
    if cached is not None:
        return bool(cached)
    try:
        inspector = inspect(db.bind)
        schema = None if IS_SQLITE else PG_SCHEMA_NAME
        available = inspector.has_table("production_order_costs", schema=schema)
        if not available:
            has_orders = inspector.has_table("production_orders", schema=schema)
            has_drivers = inspector.has_table("production_cost_drivers", schema=schema)
            if has_orders and has_drivers:
                ProductionOrderCost.__table__.create(bind=db.bind, checkfirst=True)
                inspector = inspect(db.bind)
                available = inspector.has_table("production_order_costs", schema=schema)
                if available:
                    logger.warning(
                        "Auto-created missing production_order_costs table. "
                        "Apply the corresponding SQL migration in ops/migrations to persist the schema history."
                    )
            else:
                logger.warning(
                    "production_order_costs table is missing and cannot be auto-created "
                    "(production_orders=%s, production_cost_drivers=%s)",
                    has_orders,
                    has_drivers,
                )

        if available:
            _ensure_order_costs_indexes_and_rls(db)
    except Exception:
        logger.exception("Could not ensure production_order_costs storage")
        db.rollback()
        available = False
    db.info["production_order_costs_available"] = available
    return available


def _serialize_order_cost(cost: ProductionOrderCost) -> OrderCostResponse:
    driver = cost.driver
    return OrderCostResponse(
        id=cost.id,
        order_id=cost.order_id,
        driver_id=cost.driver_id,
        qty_actual=cost.qty_actual,
        headcount_actual=cost.headcount_actual,
        rate_applied=cost.rate_applied,
        notes=cost.notes,
        cost_total=cost.cost_total,
        created_at=cost.created_at,
        driver_code=driver.code if driver else None,
        driver_name=driver.name if driver else None,
        driver_unit=driver.unit if driver else None,
    )


def _resolve_order_cost_total(cost: ProductionOrderCost) -> Decimal:
    stored_total = getattr(cost, "cost_total", None)
    if stored_total is not None:
        return Decimal(str(stored_total))
    qty_actual = Decimal(str(cost.qty_actual or 0))
    rate_applied = Decimal(str(cost.rate_applied or 0))
    headcount_actual = Decimal(str(cost.headcount_actual or 1))
    return qty_actual * rate_applied * headcount_actual


def _seed_default_order_costs(db: Session, order: ProductionOrder) -> None:
    if not _order_costs_storage_available(db):
        return

    existing_cost = (
        db.query(ProductionOrderCost).filter(ProductionOrderCost.order_id == order.id).first()
    )
    if existing_cost:
        return

    recipe = (
        db.execute(
            select(Recipe).where(Recipe.id == order.recipe_id, Recipe.tenant_id == order.tenant_id)
        ).scalar_one_or_none()
    )
    if not recipe:
        return

    yield_qty = Decimal(str(recipe.yield_qty or 0))
    qty_source = Decimal(str(order.qty_produced or order.qty_planned or 0))
    if yield_qty <= 0 or qty_source <= 0:
        return

    scale_factor = qty_source / yield_qty
    if scale_factor <= 0:
        return

    try:
        full_cost = calculate_recipe_full_cost(db, order.recipe_id)
    except Exception:
        logger.exception("Could not preload default order costs for order %s", order.id)
        return

    for line in full_cost.get("cost_lines", []) or []:
        driver_id = line.get("driver_id")
        if not driver_id:
            continue
        qty_actual = Decimal(str(line.get("qty_standard") or 0)) * scale_factor
        rate_applied = Decimal(
            str(line.get("effective_rate") or line.get("driver_default_rate") or 0)
        )
        headcount_actual = int(line.get("headcount") or 1)
        if qty_actual <= 0 and rate_applied <= 0:
            continue
        db.add(
            ProductionOrderCost(
                order_id=order.id,
                driver_id=UUID(str(driver_id)),
                qty_actual=qty_actual.quantize(Decimal("0.0001")),
                headcount_actual=max(headcount_actual, 1),
                rate_applied=rate_applied.quantize(Decimal("0.0001")),
                notes=line.get("notes") or "Auto-cargado desde costos de la receta",
            )
        )


def _generate_next_numero(db: Session, tenant_id: UUID) -> str:
    year = datetime.now(UTC).year
    prefix = f"OP-{year}-"
    table_name = ProductionOrder.__table__.fullname
    stmt = text(
        f"""
        SELECT order_number
        FROM {table_name}
        WHERE tenant_id = :tenant_id
          AND order_number LIKE :prefix
        ORDER BY order_number DESC
        LIMIT 1
        """
    )
    last_numero = db.execute(stmt, {"tenant_id": str(tenant_id), "prefix": f"{prefix}%"}).scalar()
    if last_numero:
        try:
            last_num = int(str(last_numero).split("-")[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}{next_num:04d}"


def _generate_batch_number(db: Session, tenant_id: UUID) -> str:
    year = datetime.now(UTC).year
    month = datetime.now(UTC).month
    prefix = f"LOT-{year}{month:02d}-"
    table_name = ProductionOrder.__table__.fullname
    stmt = text(
        f"""
        SELECT batch_number
        FROM {table_name}
        WHERE tenant_id = :tenant_id
          AND batch_number IS NOT NULL
          AND batch_number LIKE :prefix
        ORDER BY batch_number DESC
        LIMIT 1
        """
    )
    last_batch = db.execute(stmt, {"tenant_id": str(tenant_id), "prefix": f"{prefix}%"}).scalar()
    if last_batch:
        try:
            last_num = int(str(last_batch).split("-")[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}{next_num:04d}"


async def _create_stock_moves_for_ingredients(
    db: Session, order: ProductionOrder, warehouse_id: UUID | None = None
) -> list[UUID]:
    if not warehouse_id:
        raise ValueError("Warehouse is required to consume ingredients")

    from app.models.core.products import Product as _Product
    from app.models.recipes import RecipeIngredient as _RecipeIngredient
    from app.utils.unit_converter import are_compatible_units, convert

    stock_move_ids = []
    for line in order.lines:
        qty_consumed_raw = abs(float(line.qty_consumed))
        line_unit = (line.unit or "unit").strip()

        # Load product to get its base unit for unit conversion
        prod = (
            db.query(_Product)
            .filter(
                _Product.id == line.ingredient_product_id,
                _Product.tenant_id == order.tenant_id,
            )
            .first()
        )
        product_unit = (prod.unit if prod else None) or "unit"

        # Convert qty from recipe unit to product's stock unit.
        # Strategy 1: standard metric conversion (e.g. g → kg, lb → oz).
        # Strategy 2: package-based conversion for non-metric units (e.g. g → bloque,
        #   uds → Cubeta) using RecipeIngredient.qty_per_package as conversion factor.
        stock_qty = qty_consumed_raw
        if line_unit == product_unit:
            pass  # same unit, nothing to convert
        elif are_compatible_units(line_unit, product_unit):
            try:
                stock_qty = convert(qty_consumed_raw, line_unit, product_unit)
            except ValueError:
                pass  # fallback to raw qty
        else:
            # Non-metric units: use qty_per_package from recipe ingredient.
            # Example: levadura 170 g, qty_per_package=500 g/bloque → 0.34 bloques
            # Example: huevos 12 uds, qty_per_package=30 uds/Cubeta → 0.4 Cubetas
            ingredient = (
                db.query(_RecipeIngredient)
                .filter(
                    _RecipeIngredient.recipe_id == order.recipe_id,
                    _RecipeIngredient.product_id == line.ingredient_product_id,
                )
                .first()
            )
            if ingredient and float(ingredient.qty_per_package or 0) > 0:
                pkg_unit = (ingredient.package_unit or "").strip()
                pkg_qty = float(ingredient.qty_per_package)
                # Convert recipe qty to the package_unit first if needed
                qty_in_pkg_unit = qty_consumed_raw
                if pkg_unit and pkg_unit != line_unit and are_compatible_units(line_unit, pkg_unit):
                    try:
                        qty_in_pkg_unit = convert(qty_consumed_raw, line_unit, pkg_unit)
                    except ValueError:
                        pass
                stock_qty = qty_in_pkg_unit / pkg_qty

        stock_move = StockMove(
            tenant_id=order.tenant_id,
            kind="production_consume",
            product_id=line.ingredient_product_id,
            qty=-stock_qty,
            warehouse_id=warehouse_id,
            ref_type="production_order",
            ref_id=str(order.id),
            occurred_at=datetime.now(UTC),
        )
        db.add(stock_move)
        db.flush()
        line.stock_move_id = stock_move.id
        stock_move_ids.append(stock_move.id)
        stmt = select(StockItem).where(
            StockItem.tenant_id == order.tenant_id,
            StockItem.product_id == line.ingredient_product_id,
        )
        if warehouse_id:
            stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
        result = db.execute(stmt)
        stock_item = result.scalar_one_or_none()
        if stock_item:
            stock_item.qty = float(stock_item.qty or 0) - stock_qty
        else:
            new_stock_item = StockItem(
                tenant_id=order.tenant_id,
                product_id=line.ingredient_product_id,
                warehouse_id=warehouse_id,
                qty=-stock_qty,
            )
            db.add(new_stock_item)
        db.flush()
        # Sync aggregated stock back to products.stock for this ingredient
        try:
            from sqlalchemy import func as _func

            total_qty = (
                db.query(_func.coalesce(_func.sum(StockItem.qty), 0.0))
                .filter(
                    StockItem.product_id == line.ingredient_product_id,
                    StockItem.tenant_id == order.tenant_id,
                )
                .scalar()
            ) or 0.0
            if prod:
                prod.stock = float(total_qty)
                db.add(prod)
        except Exception:
            pass
    return stock_move_ids


async def _create_stock_move_for_output(
    db: Session, order: ProductionOrder, warehouse_id: UUID | None = None
) -> UUID:
    if not warehouse_id:
        raise ValueError("Warehouse is required to receive produced stock")
    stock_move = StockMove(
        tenant_id=order.tenant_id,
        kind="production_output",
        product_id=order.product_id,
        qty=abs(float(order.qty_produced)),
        warehouse_id=warehouse_id,
        ref_type="production_order",
        ref_id=str(order.id),
        lot=order.batch_number,
        occurred_at=datetime.now(UTC),
    )
    db.add(stock_move)
    db.flush()
    stmt = select(StockItem).where(
        StockItem.tenant_id == order.tenant_id,
        StockItem.product_id == order.product_id,
    )
    if warehouse_id:
        stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
    if order.batch_number:
        stmt = stmt.where(StockItem.lot == order.batch_number)
    else:
        stmt = stmt.where(StockItem.lot.is_(None))
    result = db.execute(stmt)
    stock_item = result.scalar_one_or_none()
    if stock_item:
        stock_item.qty = float(stock_item.qty or 0) + abs(float(order.qty_produced))
    else:
        new_stock_item = StockItem(
            tenant_id=order.tenant_id,
            product_id=order.product_id,
            warehouse_id=warehouse_id,
            qty=abs(float(order.qty_produced)),
            lot=order.batch_number,
        )
        db.add(new_stock_item)
    db.flush()

    # Sync aggregated stock back to products.stock
    try:
        from sqlalchemy import func as _func

        total_qty = (
            db.query(_func.coalesce(_func.sum(StockItem.qty), 0.0))
            .filter(
                StockItem.product_id == order.product_id, StockItem.tenant_id == order.tenant_id
            )
            .scalar()
        ) or 0.0
        from app.models.core.products import Product as _Product

        prod = (
            db.query(_Product)
            .filter(_Product.id == order.product_id, _Product.tenant_id == order.tenant_id)
            .first()
        )
        if prod:
            prod.stock = float(total_qty)
            db.add(prod)
    except Exception:
        pass

    return stock_move.id


def _resolve_warehouse_id(db: Session, tenant_id: UUID, preferred: UUID | None = None) -> UUID:
    if preferred:
        return UUID(str(_require_warehouse_for_tenant(db, tenant_id, preferred).id))
    # Try to find from stock items first
    stmt = (
        select(StockItem.warehouse_id)
        .where(StockItem.tenant_id == tenant_id)
        .order_by(StockItem.warehouse_id.asc())
        .limit(1)
    )
    warehouse_id = db.execute(stmt).scalar_one_or_none()
    if warehouse_id:
        return warehouse_id
    # Fallback: find any active warehouse for this tenant
    wh_stmt = (
        select(Warehouse.id)
        .where(Warehouse.tenant_id == str(tenant_id), Warehouse.is_active.is_(True))
        .order_by(Warehouse.id.asc())
        .limit(1)
    )
    warehouse_id = db.execute(wh_stmt).scalar_one_or_none()
    if not warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no_warehouse_available",
        )
    return UUID(str(warehouse_id))


def _create_expense_for_completed_production(
    db: Session,
    order: ProductionOrder,
    tenant_id: UUID,
    user_id: UUID,
) -> None:
    # Idempotency: avoid duplicate expenses for the same production order.
    invoice_number = f"PROD-{getattr(order, 'order_number', '') or getattr(order, 'numero', '')}"
    existing = (
        db.query(Expense)
        .filter(
            Expense.tenant_id == tenant_id,
            Expense.invoice_number == invoice_number,
        )
        .first()
    )

    recipe_name = "Production"
    try:
        recipe = (
            db.execute(
                select(Recipe).where(
                    Recipe.id == order.recipe_id,
                    Recipe.tenant_id == order.tenant_id,
                )
            ).scalar_one_or_none()
        )
        if recipe and recipe.name:
            recipe_name = str(recipe.name)
    except Exception:
        pass

    # Recompute from recipe ingredient unit costs to avoid inflated totals when
    # line cost_unit was stored as package cost by legacy logic.
    recipe_ingredients = (
        db.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == order.recipe_id))
        .scalars()
        .all()
    )
    unit_cost_by_product: dict[UUID, Decimal] = {}
    for ing in recipe_ingredients:
        ing_qty = Decimal(str(ing.qty or 0))
        ingredient_cost = Decimal(str(ing.ingredient_cost or 0))
        qty_per_package = Decimal(str(ing.qty_per_package or 0))
        package_cost = Decimal(str(ing.package_cost or 0))
        unit_cost = Decimal("0")
        if ing_qty > 0 and ingredient_cost > 0:
            unit_cost = ingredient_cost / ing_qty
        elif qty_per_package > 0 and package_cost >= 0:
            unit_cost = package_cost / qty_per_package
        unit_cost_by_product[ing.product_id] = unit_cost

    total_cost = Decimal("0")
    for line in order.lines:
        qty_source = line.qty_consumed
        if qty_source is None or qty_source <= 0:
            qty_source = line.qty_required
        qty = Decimal(str(qty_source or 0))
        if qty <= 0:
            continue
        unit_cost = unit_cost_by_product.get(
            line.ingredient_product_id, Decimal(str(line.cost_unit or 0))
        )
        total_cost += qty * unit_cost

    if _order_costs_storage_available(db):
        order_costs = (
            db.query(ProductionOrderCost).filter(ProductionOrderCost.order_id == order.id).all()
        )
        for cost in order_costs:
            total_cost += _resolve_order_cost_total(cost)

    qty = Decimal(str(order.qty_produced or 0))
    concept = f"Production cost - {recipe_name} ({qty})"
    notes = (
        f"Auto-generated from production order {getattr(order, 'order_number', '') or getattr(order, 'numero', '')}. "
        f"Recipe: {recipe_name}. Qty produced: {qty}."
    )

    if existing:
        existing.date = datetime.now(UTC).date()
        existing.concept = concept
        existing.category = "production"
        existing.subcategory = "manufacturing"
        existing.amount = total_cost
        existing.vat = Decimal("0")
        existing.total = total_cost
        existing.supplier_id = None
        existing.payment_method = None
        existing.status = "paid"
        existing.user_id = user_id
        existing.notes = notes
        return

    expense = Expense(
        tenant_id=tenant_id,
        date=datetime.now(UTC).date(),
        concept=concept,
        category="production",
        subcategory="manufacturing",
        amount=total_cost,
        vat=Decimal("0"),
        total=total_cost,
        supplier_id=None,
        payment_method=None,
        invoice_number=invoice_number,
        status="paid",
        user_id=user_id,
        notes=notes,
    )
    db.add(expense)


# ÓRDENES DE PRODUCCIÓN
@router.get("/orders", response_model=ProductionOrderList)
async def list_production_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None),
    recipe_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    scheduled_from: str | None = Query(None),
    scheduled_to: str | None = Query(None),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    query = select(ProductionOrder).where(ProductionOrder.tenant_id == tenant_id)
    if status:
        query = query.where(ProductionOrder.status == status.upper())
    if recipe_id:
        query = query.where(ProductionOrder.recipe_id == recipe_id)
    if date_from:
        query = query.where(ProductionOrder.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(ProductionOrder.created_at <= datetime.fromisoformat(date_to))
    if scheduled_from:
        query = query.where(
            ProductionOrder.scheduled_date >= datetime.fromisoformat(scheduled_from)
        )
    if scheduled_to:
        query = query.where(ProductionOrder.scheduled_date <= datetime.fromisoformat(scheduled_to))
    query = query.order_by(ProductionOrder.created_at.desc())
    count_query = select(func.count()).select_from(query.subquery())
    total_result = db.execute(count_query)
    total = total_result.scalar() or 0
    result = db.execute(query.offset(skip).limit(limit))
    orders = result.scalars().all()
    return ProductionOrderList(items=orders, total=total, skip=skip, limit=limit)


@router.get("/planning/suggestions", response_model=list[ProductionPlanningSuggestion])
async def list_production_planning_suggestions(
    target_date: date | None = Query(None),
    history_days: int = Query(14, ge=1, le=90),
    limit: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    target_day = target_date or datetime.now(UTC).date()
    window_start = target_day - timedelta(days=history_days)
    window_end = target_day

    sales_rows = (
        db.query(
            POSReceiptLine.product_id.label("product_id"),
            func.coalesce(func.sum(POSReceiptLine.qty), 0).label("qty_sold"),
        )
        .join(POSReceipt, POSReceipt.id == POSReceiptLine.receipt_id)
        .filter(POSReceipt.tenant_id == tenant_id)
        .filter(POSReceipt.status.in_(["paid", "invoiced"]))
        .filter(func.date(POSReceipt.created_at) >= window_start)
        .filter(func.date(POSReceipt.created_at) < window_end)
        .group_by(POSReceiptLine.product_id)
        .all()
    )
    sold_by_product = {row.product_id: Decimal(str(row.qty_sold or 0)) for row in sales_rows}
    if not sold_by_product:
        return []

    planned_rows = (
        db.query(
            ProductionOrder.product_id.label("product_id"),
            func.coalesce(func.sum(ProductionOrder.qty_planned), 0).label("qty_planned"),
        )
        .filter(ProductionOrder.tenant_id == tenant_id)
        .filter(ProductionOrder.status != "CANCELLED")
        .filter(func.date(ProductionOrder.scheduled_date) == target_day)
        .group_by(ProductionOrder.product_id)
        .all()
    )
    planned_by_product = {
        row.product_id: Decimal(str(row.qty_planned or 0)) for row in planned_rows
    }

    stock_rows = (
        db.query(
            StockItem.product_id.label("product_id"),
            func.coalesce(func.sum(StockItem.qty), 0).label("qty_on_hand"),
        )
        .filter(StockItem.tenant_id == tenant_id)
        .group_by(StockItem.product_id)
        .all()
    )
    stock_by_product = {row.product_id: Decimal(str(row.qty_on_hand or 0)) for row in stock_rows}

    recipes = (
        db.query(Recipe, Product)
        .join(Product, Product.id == Recipe.product_id)
        .filter(Recipe.tenant_id == tenant_id, Recipe.is_active.is_(True))
        .all()
    )

    suggestions: list[ProductionPlanningSuggestion] = []
    for recipe, product in recipes:
        product_id = recipe.product_id
        sold_qty = sold_by_product.get(product_id, Decimal("0"))
        if sold_qty <= 0:
            continue

        avg_daily_sales = (sold_qty / Decimal(str(history_days))).quantize(Decimal("0.001"))
        planned_qty = planned_by_product.get(product_id, Decimal("0"))
        stock_on_hand = stock_by_product.get(product_id, Decimal("0"))
        suggested_qty = Decimal(
            str(max(math.ceil(float(avg_daily_sales - planned_qty - stock_on_hand)), 0))
        )
        if suggested_qty <= 0:
            continue

        suggestions.append(
            ProductionPlanningSuggestion(
                recipe_id=recipe.id,
                product_id=product_id,
                recipe_name=str(recipe.name or ""),
                product_name=str(product.name or ""),
                target_date=target_day.isoformat(),
                avg_daily_sales=avg_daily_sales,
                stock_on_hand=stock_on_hand.quantize(Decimal("0.001")),
                already_planned_qty=planned_qty.quantize(Decimal("0.001")),
                suggested_qty=suggested_qty,
            )
        )

    suggestions.sort(key=lambda item: float(item.suggested_qty), reverse=True)
    return suggestions[:limit]


@router.post("/orders", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_production_order(
    order_in: ProductionOrderCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])
    recipe = _require_recipe_for_tenant(db, tenant_id, order_in.recipe_id)
    product = _require_product_for_tenant(db, tenant_id, order_in.product_id)
    if order_in.warehouse_id is not None:
        _require_warehouse_for_tenant(db, tenant_id, order_in.warehouse_id)
    if UUID(str(recipe.product_id)) != product.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipe_product_mismatch",
        )
    numero = _generate_next_numero(db, tenant_id)
    order = ProductionOrder(
        tenant_id=tenant_id,
        numero=numero,
        recipe_id=order_in.recipe_id,
        product_id=order_in.product_id,
        warehouse_id=order_in.warehouse_id,
        qty_planned=order_in.qty_planned,
        scheduled_date=order_in.scheduled_date,
        notes=order_in.notes,
        status="DRAFT",
        created_by=user_id,
    )
    db.add(order)
    db.flush()
    if order_in.lines:
        for line_in in order_in.lines:
            if line_in.qty_required <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="line_qty_required_must_be_positive",
                )
            line = ProductionOrderLine(
                order_id=order.id,
                ingredient_product_id=line_in.ingredient_product_id,
                qty_required=line_in.qty_required,
                qty_consumed=line_in.qty_consumed,
                unit=line_in.unit,
                cost_unit=line_in.cost_unit,
            )
            line.cost_total = line.qty_required * line.cost_unit
            db.add(line)
    else:
        ingredients_stmt = select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        ingredients_result = db.execute(ingredients_stmt)
        ingredients = ingredients_result.scalars().all()
        yield_qty = Decimal(str(recipe.yield_qty or 0))
        if yield_qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recipe_invalid_yield_qty",
            )
        scale_factor = Decimal(str(order_in.qty_planned)) / yield_qty
        created_lines = 0
        for ing in ingredients:
            ing_qty = Decimal(str(ing.qty or 0))
            qty_required = (ing_qty * scale_factor).quantize(Decimal("0.001"))
            if qty_required <= 0:
                continue
            qty_per_package = Decimal(str(ing.qty_per_package or 0))
            package_cost = Decimal(str(ing.package_cost or 0))
            ingredient_cost = Decimal(str(ing.ingredient_cost or 0))
            if ing_qty > 0 and ingredient_cost > 0:
                unit_cost = ingredient_cost / ing_qty
            else:
                unit_cost = (
                    (package_cost / qty_per_package) if qty_per_package > 0 else Decimal("0")
                )
            line = ProductionOrderLine(
                order_id=order.id,
                ingredient_product_id=ing.product_id,
                qty_required=qty_required,
                qty_consumed=Decimal("0"),
                unit=ing.unit or "unit",
                cost_unit=unit_cost,
            )
            line.cost_total = line.qty_required * line.cost_unit
            db.add(line)
            created_lines += 1
        if created_lines == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La receta no tiene ingredientes validos para la cantidad solicitada",
            )
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/{order_id}/costs", response_model=list[OrderCostResponse])
def list_order_costs(
    order_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    order = db.execute(
        select(ProductionOrder).where(
            ProductionOrder.id == order_id,
            ProductionOrder.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if not _order_costs_storage_available(db):
        return []

    costs = (
        db.query(ProductionOrderCost)
        .filter(ProductionOrderCost.order_id == order.id)
        .order_by(ProductionOrderCost.created_at.asc())
        .all()
    )
    return [_serialize_order_cost(cost) for cost in costs]


@router.put("/orders/{order_id}/costs", response_model=list[OrderCostResponse])
def replace_order_costs(
    order_id: UUID,
    items: list[OrderCostCreate] = Body(default=[]),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    order = db.execute(
        select(ProductionOrder).where(
            ProductionOrder.id == order_id,
            ProductionOrder.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if order.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden editar costos de una orden completada",
        )
    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden editar costos de una orden cancelada",
        )
    if not _order_costs_storage_available(db):
        return []

    driver_ids = {item.driver_id for item in items}
    if driver_ids:
        valid_driver_ids = {
            row[0]
            for row in db.execute(
                select(ProductionCostDriver.id).where(
                    ProductionCostDriver.tenant_id == tenant_id,
                    ProductionCostDriver.id.in_(driver_ids),
                )
            ).all()
        }
        missing = driver_ids - valid_driver_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uno o más gastos usan drivers no válidos para este tenant",
            )

    (
        db.query(ProductionOrderCost)
        .filter(ProductionOrderCost.order_id == order.id)
        .delete(synchronize_session=False)
    )

    for item in items:
        db.add(
            ProductionOrderCost(
                order_id=order.id,
                driver_id=item.driver_id,
                qty_actual=item.qty_actual,
                headcount_actual=item.headcount_actual,
                rate_applied=item.rate_applied,
                notes=item.notes,
            )
        )

    db.commit()
    costs = (
        db.query(ProductionOrderCost)
        .filter(ProductionOrderCost.order_id == order.id)
        .order_by(ProductionOrderCost.created_at.asc())
        .all()
    )
    return [_serialize_order_cost(cost) for cost in costs]


@router.get("/orders/{order_id}", response_model=ProductionOrderResponse)
async def get_production_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    return order


@router.put("/orders/{order_id}", response_model=ProductionOrderResponse)
async def update_production_order(
    order_id: UUID,
    order_in: ProductionOrderUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if order.status not in ["DRAFT", "SCHEDULED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede editar orden en estado {order.status}",
        )
    update_data = order_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if order.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar órdenes en estado DRAFT",
        )
    db.delete(order)
    db.commit()


@router.post("/orders/{order_id}/start", response_model=ProductionOrderResponse)
async def start_production(
    order_id: UUID,
    request: ProductionOrderStartRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if order.status not in ["DRAFT", "SCHEDULED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede iniciar orden en estado {order.status}",
        )
    order.status = "IN_PROGRESS"
    order.started_at = request.started_at or datetime.now(UTC)
    if request.notes:
        order.notes = (order.notes or "") + f"\n[Inicio] {request.notes}"
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/complete", response_model=ProductionOrderResponse)
async def complete_production(
    order_id: UUID,
    request: ProductionOrderCompleteRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    raw_user_id = claims.get("user_id")
    try:
        user_id = UUID(str(raw_user_id)) if raw_user_id else UUID(str(order_id))
    except Exception:
        user_id = UUID(str(order_id))
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if order.status in ["DRAFT", "SCHEDULED"]:
        order.started_at = order.started_at or request.completed_at or datetime.now(UTC)
        order.status = "IN_PROGRESS"
    elif order.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden completar órdenes en estado IN_PROGRESS (actual: {order.status})",
        )
    order.qty_produced = request.qty_produced
    order.waste_qty = request.waste_qty
    order.waste_reason = request.waste_reason
    order.completed_at = request.completed_at or datetime.now(UTC)
    order.status = "COMPLETED"
    if not order.batch_number:
        order.batch_number = request.batch_number or _generate_batch_number(db, tenant_id)
    warehouse_id = _resolve_warehouse_id(db, tenant_id, order.warehouse_id)
    order.warehouse_id = warehouse_id
    if request.notes:
        order.notes = (order.notes or "") + f"\n[Completado] {request.notes}"
    for line in order.lines:
        if not line.qty_consumed or line.qty_consumed == 0:
            line.qty_consumed = line.qty_required
    try:
        await _create_stock_moves_for_ingredients(db, order, warehouse_id)
        await _create_stock_move_for_output(db, order, warehouse_id)
        try:
            _seed_default_order_costs(db, order)
            _create_expense_for_completed_production(db, order, tenant_id, user_id)
        except Exception as expense_exc:
            # Do not block production completion if expense posting fails.
            logger.exception(
                "Production completed but expense auto-post failed for order %s: %s",
                order.id,
                expense_exc,
            )
        db.commit()
        db.refresh(order)
        return order
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear movimientos de stock: {str(e)}",
        )


@router.post("/orders/{order_id}/cancel", response_model=ProductionOrderResponse)
async def cancel_production(
    order_id: UUID,
    reason: str | None = Query(None),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada"
        )
    if order.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar una orden completada",
        )
    order.status = "CANCELLED"
    if reason:
        order.notes = (order.notes or "") + f"\n[Cancelado] {reason}"
    db.commit()
    db.refresh(order)
    return order


@router.post("/calculator", response_model=ProductionCalculatorResponse)
async def calculate_production(
    request: ProductionCalculatorRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = _require_recipe_for_tenant(db, tenant_id, request.recipe_id)
    ingredients_stmt = select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    ingredients_result = db.execute(ingredients_stmt)
    ingredients = ingredients_result.scalars().all()
    yield_qty = float(recipe.yield_qty) if recipe.yield_qty else 1.0
    scale_factor = float(request.qty_desired) / yield_qty if yield_qty > 0 else 1.0
    all_ingredients = []
    missing_ingredients = []
    total_cost = Decimal("0")
    can_produce = True
    for ing in ingredients:
        qty_required = Decimal(str(float(ing.qty) * scale_factor))
        stock_stmt = select(func.sum(StockItem.qty)).where(
            StockItem.tenant_id == tenant_id,
            StockItem.product_id == ing.product_id,
        )
        stock_result = db.execute(stock_stmt)
        stock_available = stock_result.scalar() or Decimal("0")
        stock_sufficient = stock_available >= qty_required
        qty_to_purchase = max(Decimal("0"), qty_required - stock_available)
        qty_per_package = Decimal(str(ing.qty_per_package or 0))
        package_cost = Decimal(str(ing.package_cost or 0))
        cost_unit = (package_cost / qty_per_package) if qty_per_package > 0 else Decimal("0")
        total_cost += qty_required * cost_unit
        ingredient_req = IngredientRequirement(
            ingredient_id=ing.product_id,
            ingredient_name=ing.product_id,
            qty_required=qty_required,
            unit=ing.unit or "unit",
            stock_available=stock_available,
            stock_sufficient=stock_sufficient,
            qty_to_purchase=qty_to_purchase,
        )
        all_ingredients.append(ingredient_req)
        if not stock_sufficient:
            missing_ingredients.append(ingredient_req)
            can_produce = False
    qty_producible = request.qty_desired
    if missing_ingredients:
        min_ratio = float("inf")
        for ing_data in ingredients:
            stock_stmt = select(func.sum(StockItem.qty)).where(
                StockItem.tenant_id == tenant_id,
                StockItem.product_id == ing_data.product_id,
            )
            stock_result = db.execute(stock_stmt)
            stock_qty = float(stock_result.scalar() or 0)
            ing_qty_per_unit = float(ing_data.qty) / yield_qty if yield_qty > 0 else 0
            if ing_qty_per_unit > 0:
                ratio = stock_qty / ing_qty_per_unit
                min_ratio = min(min_ratio, ratio)
        qty_producible = Decimal(str(min_ratio)) if min_ratio != float("inf") else Decimal("0")
    return ProductionCalculatorResponse(
        recipe_id=recipe.id,
        recipe_name=recipe.name or "Sin nombre",
        qty_desired=request.qty_desired,
        qty_producible=qty_producible,
        can_produce=can_produce,
        missing_ingredients=missing_ingredients,
        all_ingredients=all_ingredients,
        estimated_cost=total_cost,
        production_time_minutes=recipe.prep_time_minutes,
    )


@router.get("/stats", response_model=ProductionOrderStats)
async def get_production_stats(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    query = select(ProductionOrder).where(ProductionOrder.tenant_id == tenant_id)
    if date_from:
        query = query.where(ProductionOrder.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(ProductionOrder.created_at <= datetime.fromisoformat(date_to))
    result = db.execute(query)
    orders = result.scalars().all()
    stats = ProductionOrderStats()
    for order in orders:
        stats.total_orders += 1
        if order.status == "COMPLETED":
            stats.completed += 1
            stats.total_qty_produced += order.qty_produced
            stats.total_waste_qty += order.waste_qty
            if order.started_at and order.completed_at:
                duration = (order.completed_at - order.started_at).total_seconds() / 3600
                stats.avg_production_time_hours += duration
        elif order.status == "IN_PROGRESS":
            stats.in_progress += 1
        elif order.status == "SCHEDULED":
            stats.scheduled += 1
        elif order.status == "CANCELLED":
            stats.cancelled += 1
    if stats.completed > 0:
        stats.avg_production_time_hours = stats.avg_production_time_hours / stats.completed
        if stats.total_qty_produced > 0:
            waste_pct = (float(stats.total_waste_qty) / float(stats.total_qty_produced)) * 100
            stats.waste_percentage = round(waste_pct, 2)
    return stats


# RECETAS
@router.get("/recipes", response_model=list[RecipeDetailResponse] | list[RecipeResponse])
def list_recipes(
    is_active: bool | None = None,
    product_id: UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=5000),
    include_ingredients: bool = Query(
        default=False,
        description="Incluir ingredientes en la respuesta. El modelo ya usa selectin por lo que no genera queries adicionales.",
    ),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    query = db.query(Recipe).filter(Recipe.tenant_id == tenant_id)
    if is_active is not None:
        query = query.filter(Recipe.is_active == is_active)
    if product_id:
        query = query.filter(Recipe.product_id == product_id)
    recipes = query.offset(skip).limit(limit).all()
    if include_ingredients:
        return [RecipeDetailResponse.model_validate(r) for r in recipes]
    return recipes


@router.post("/recipes", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    recipe_data: RecipeCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    # Verificar que product_id pertenece al tenant
    from app.models.core.products import Product as ProductModel

    if recipe_data.product_id:
        product = (
            db.query(ProductModel)
            .filter(
                ProductModel.id == recipe_data.product_id,
                ProductModel.tenant_id == tenant_id,
            )
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="product_not_found_or_unauthorized"
            )
    recipe = Recipe(
        tenant_id=tenant_id,
        product_id=recipe_data.product_id,
        name=recipe_data.name,
        yield_qty=recipe_data.yield_qty,
        prep_time_minutes=recipe_data.prep_time_minutes,
        baking_time_minutes=recipe_data.baking_time_minutes,
        oven_temp_celsius=recipe_data.oven_temp_celsius,
        rest_time_minutes=recipe_data.rest_time_minutes,
        touch_minutes_standard=recipe_data.touch_minutes_standard or 0,
        oven_minutes_standard=recipe_data.oven_minutes_standard or 0,
        process_minutes=recipe_data.process_minutes,
        waste_pct=recipe_data.waste_pct,
        trays_per_batch=recipe_data.trays_per_batch,
        units_per_tray=recipe_data.units_per_tray,
        instructions=recipe_data.instructions,
        is_active=recipe_data.is_active if recipe_data.is_active is not None else True,
        total_cost=0,
    )
    db.add(recipe)
    db.flush()
    if recipe_data.ingredients:
        for idx, ing_data in enumerate(recipe_data.ingredients):
            ingrediente = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=ing_data.product_id,
                qty=ing_data.qty,
                unit=ing_data.unit,
                purchase_packaging=ing_data.purchase_packaging,
                qty_per_package=ing_data.qty_per_package,
                package_unit=ing_data.package_unit,
                package_cost=ing_data.package_cost,
                notes=ing_data.notes,
                line_order=ing_data.line_order if ing_data.line_order is not None else idx,
            )
            db.add(ingrediente)
            ingredient_product = (
                db.query(ProductModel)
                .filter(
                    ProductModel.id == ing_data.product_id,
                    ProductModel.tenant_id == tenant_id,
                )
                .first()
            )
            sync_product_as_raw_material_from_recipe_line(
                db,
                tenant_id=tenant_id,
                product=ingredient_product,
                unit=ing_data.unit,
                package_unit=ing_data.package_unit,
            )
    db.commit()
    db.refresh(recipe)
    try:
        calculate_recipe_cost(db, recipe.id)
        db.refresh(recipe)
    except Exception:
        pass
    return recipe


@router.get("/recipes/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
    return recipe


@router.post(
    "/recipes/{recipe_id}/optimize",
    response_model=RecipeOptimizationResponse,
)
async def optimize_recipe(
    recipe_id: UUID,
    payload: RecipeOptimizationRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    _flags=Depends(require_flag("copilot_enabled")),
):
    tenant_id = UUID(claims["tenant_id"])
    user_id = str(claims.get("user_id")) if claims.get("user_id") else None
    try:
        return await optimize_recipe_with_ai(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            recipe_id=recipe_id,
            request=payload,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "recipe_not_found":
            raise HTTPException(status_code=404, detail=detail) from exc
        if detail == "recipe_has_no_ingredients":
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=503, detail=detail) from exc


@router.put("/recipes/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: UUID,
    recipe_data: RecipeUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
    update_data = recipe_data.dict(exclude_unset=True)
    ingredients_payload = update_data.pop("ingredients", None)

    for key, value in update_data.items():
        setattr(recipe, key, value)

    # If ingredients are provided on update, replace current recipe ingredients
    # with the submitted list (full-sync behavior from UI form).
    if ingredients_payload is not None:
        (
            db.query(RecipeIngredient)
            .filter(RecipeIngredient.recipe_id == recipe_id)
            .delete(synchronize_session=False)
        )
        for idx, ing_data in enumerate(ingredients_payload):
            ingrediente = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=ing_data["product_id"],
                qty=ing_data["qty"],
                unit=ing_data["unit"],
                purchase_packaging=ing_data["purchase_packaging"],
                qty_per_package=ing_data["qty_per_package"],
                package_unit=ing_data["package_unit"],
                package_cost=ing_data["package_cost"],
                notes=ing_data.get("notes"),
                line_order=ing_data.get("line_order", idx),
            )
            db.add(ingrediente)
            ingredient_product = (
                db.query(Product)
                .filter(
                    Product.id == ing_data["product_id"],
                    Product.tenant_id == tenant_id,
                )
                .first()
            )
            sync_product_as_raw_material_from_recipe_line(
                db,
                tenant_id=tenant_id,
                product=ingredient_product,
                unit=ing_data["unit"],
                package_unit=ing_data["package_unit"],
            )

    db.commit()
    db.refresh(recipe)
    try:
        calculate_recipe_cost(db, recipe.id)
        db.refresh(recipe)
    except Exception:
        pass
    return recipe


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
    db.delete(recipe)
    db.commit()


@router.post(
    "/recipes/{recipe_id}/ingredients",
    response_model=RecipeIngredientResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_recipe_ingredient(
    recipe_id: UUID,
    payload: RecipeIngredientCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")

    duplicate = (
        db.query(RecipeIngredient)
        .filter(
            RecipeIngredient.recipe_id == recipe_id,
            RecipeIngredient.product_id == payload.product_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ingrediente ya existe en la receta",
        )

    next_order = payload.line_order
    if next_order is None:
        current_max = (
            db.query(func.max(RecipeIngredient.line_order))
            .filter(RecipeIngredient.recipe_id == recipe_id)
            .scalar()
        )
        next_order = (current_max or 0) + 1

    ingrediente = RecipeIngredient(
        recipe_id=recipe_id,
        product_id=payload.product_id,
        qty=payload.qty,
        unit=payload.unit,
        purchase_packaging=payload.purchase_packaging,
        qty_per_package=payload.qty_per_package,
        package_unit=payload.package_unit,
        package_cost=payload.package_cost,
        notes=payload.notes,
        line_order=next_order,
    )
    db.add(ingrediente)
    ingredient_product = (
        db.query(Product)
        .filter(Product.id == payload.product_id, Product.tenant_id == tenant_id)
        .first()
    )
    sync_product_as_raw_material_from_recipe_line(
        db,
        tenant_id=tenant_id,
        product=ingredient_product,
        unit=payload.unit,
        package_unit=payload.package_unit,
    )
    db.commit()
    db.refresh(ingrediente)

    try:
        calculate_recipe_cost(db, recipe_id)
    except Exception:
        pass

    return ingrediente


@router.put(
    "/recipes/{recipe_id}/ingredients/{ingredient_id}",
    response_model=RecipeIngredientResponse,
)
def update_recipe_ingredient(
    recipe_id: UUID,
    ingredient_id: UUID,
    payload: RecipeIngredientUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    ingrediente = (
        db.query(RecipeIngredient)
        .filter(
            RecipeIngredient.id == ingredient_id,
            RecipeIngredient.recipe_id == recipe_id,
        )
        .first()
    )
    if not ingrediente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado"
        )

    data = payload.dict(exclude_unset=True)
    if "product_id" in data:
        duplicate = (
            db.query(RecipeIngredient)
            .filter(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.product_id == data["product_id"],
                RecipeIngredient.id != ingredient_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ingrediente ya existe en la receta",
            )

    for field, value in data.items():
        setattr(ingrediente, field, value)

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
    ingredient_product = (
        db.query(Product)
        .filter(
            Product.id == ingrediente.product_id,
            Product.tenant_id == tenant_id,
        )
        .first()
    )
    sync_product_as_raw_material_from_recipe_line(
        db,
        tenant_id=tenant_id,
        product=ingredient_product,
        unit=ingrediente.unit,
        package_unit=ingrediente.package_unit,
    )

    db.commit()
    db.refresh(ingrediente)

    try:
        calculate_recipe_cost(db, recipe_id)
    except Exception:
        pass

    return ingrediente


@router.delete(
    "/recipes/{recipe_id}/ingredients/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recipe_ingredient(
    recipe_id: UUID,
    ingredient_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    ingrediente = (
        db.query(RecipeIngredient)
        .filter(
            RecipeIngredient.id == ingredient_id,
            RecipeIngredient.recipe_id == recipe_id,
        )
        .first()
    )
    if not ingrediente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado"
        )

    db.delete(ingrediente)
    db.commit()

    try:
        calculate_recipe_cost(db, recipe_id)
    except Exception:
        pass


@router.post(
    "/recipes/{recipe_id}/sync-product-price",
    response_model=dict,
)
def sync_recipe_product_price(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Sincroniza el precio sugerido del producto asociado a la receta"""
    try:
        result = calculate_recipe_cost(db, recipe_id, update_product_price=True)
        return {
            "success": True,
            "recipe_id": str(recipe_id),
            "suggested_price": result["suggested_price"],
            "unit_cost": result["unit_cost"],
            "message": "Precio sugerido sincronizado con el producto",
        }
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")


@router.get(
    "/recipes/{recipe_id}/cost-breakdown",
    response_model=RecipeCostBreakdownResponse,
)
def get_recipe_cost_breakdown(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    try:
        return calculate_recipe_cost(db, recipe_id, update_product_price=False)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")


@router.post(
    "/recipes/{recipe_id}/calculate-production",
    response_model=ProductionCalculationResponse,
)
def calculate_recipe_production(
    recipe_id: UUID,
    payload: ProductionCalculationRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    try:
        calculation = calculate_purchase_for_production(db, recipe_id, payload.qty_to_produce)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")

    tiempo = None
    if payload.workers:
        try:
            tiempo = calculate_production_time(
                db, recipe_id, payload.qty_to_produce, payload.workers
            )
        except ValueError:
            tiempo = None

    return {**calculation, "tiempo_estimado": tiempo}


@router.post(
    "/recipes/{recipe_id}/purchase-order",
    response_model=PurchaseOrderResponse,
)
def create_recipe_purchase_order(
    recipe_id: UUID,
    payload: PurchaseOrderRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    try:
        return create_purchase_order_from_recipe(
            db,
            recipe_id,
            qty_to_produce=payload.qty_to_produce,
            supplier_id=payload.supplier_id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")


@router.post(
    "/recipes/{recipe_id}/profitability",
    response_model=RecipeProfitabilityResponse,
)
def recipe_profitability(
    recipe_id: UUID,
    payload: RecipeProfitabilityRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    try:
        data = get_recipe_profitability(
            db,
            recipe_id,
            selling_price=payload.selling_price,
            indirect_costs_pct=payload.indirect_costs_pct,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")

    # Uniformar campo de nombre con el esquema de respuesta
    name = data.pop("nombre", None)
    if name is not None:
        data["name"] = name

    return data


@router.post(
    "/recipes/compare",
    response_model=RecipeComparisonResponse,
)
def compare_recipes_costs(
    recipe_ids: list[UUID] = Body(..., min_length=1),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    comparisons = compare_recipe_costs(db, recipe_ids)
    for item in comparisons:
        nombre = item.get("nombre")
        if "name" not in item and nombre is not None:
            item["name"] = nombre

    return {"recipes": comparisons}


# ============================================================================
# COST DRIVER UNIT TYPES (lookup)
# ============================================================================


@router.get("/cost-driver-unit-types")
def list_cost_driver_unit_types(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """List available unit types for cost drivers.

    Falls back to the global units catalog when the tenant does not yet have a
    dedicated cost-driver unit catalog.
    """
    tenant_id = UUID(claims["tenant_id"])
    return [
        _serialize_cost_driver_unit_option(unit_option)
        for unit_option in _list_cost_driver_unit_options(db, tenant_id)
    ]


# ============================================================================
# COST DRIVERS CRUD
# ============================================================================


@router.get("/cost-drivers", response_model=list[CostDriverResponse])
def list_cost_drivers(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    return (
        db.query(ProductionCostDriver)
        .filter(ProductionCostDriver.tenant_id == tenant_id)
        .order_by(ProductionCostDriver.code)
        .all()
    )


@router.post(
    "/cost-drivers", response_model=CostDriverResponse, status_code=status.HTTP_201_CREATED
)
def create_cost_driver(
    data: CostDriverCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    existing = (
        db.query(ProductionCostDriver)
        .filter(ProductionCostDriver.tenant_id == tenant_id, ProductionCostDriver.code == data.code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un driver con código '{data.code}'")
    payload = data.model_dump()
    payload["unit"] = _resolve_cost_driver_unit_code(db, tenant_id, payload.get("unit"))
    driver = ProductionCostDriver(tenant_id=tenant_id, **payload)
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.post("/cost-drivers/apply-all-recipes", status_code=status.HTTP_200_OK)
def apply_cost_drivers_to_all_recipes(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Apply all active cost drivers to every recipe (skips if already assigned)."""
    tenant_id = UUID(claims["tenant_id"])
    drivers = (
        db.query(ProductionCostDriver)
        .filter(
            ProductionCostDriver.tenant_id == tenant_id,
            ProductionCostDriver.is_active.is_(True),
        )
        .all()
    )
    if not drivers:
        return {"ok": True, "recipes_updated": 0, "lines_added": 0}

    recipes = db.query(Recipe).filter(Recipe.tenant_id == tenant_id).all()
    lines_added = 0
    recipes_updated = 0
    for recipe in recipes:
        existing_driver_ids = {
            line.driver_id
            for line in db.query(RecipeCostLine).filter(RecipeCostLine.recipe_id == recipe.id).all()
        }
        recipe_touched = False
        for driver in drivers:
            if driver.id in existing_driver_ids:
                continue
            line = RecipeCostLine(
                recipe_id=recipe.id,
                driver_id=driver.id,
                qty_standard=Decimal("1"),
                headcount=1,
                rate_override=None,
                notes=None,
                line_order=len(existing_driver_ids) + lines_added,
            )
            db.add(line)
            lines_added += 1
            recipe_touched = True
        if recipe_touched:
            recipes_updated += 1
    db.commit()
    return {"ok": True, "recipes_updated": recipes_updated, "lines_added": lines_added}


@router.put("/cost-drivers/{driver_id}", response_model=CostDriverResponse)
def update_cost_driver(
    driver_id: UUID,
    data: CostDriverUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    driver = (
        db.query(ProductionCostDriver)
        .filter(ProductionCostDriver.id == driver_id, ProductionCostDriver.tenant_id == tenant_id)
        .first()
    )
    if not driver:
        raise HTTPException(status_code=404, detail="Cost driver no encontrado")
    payload = data.model_dump(exclude_unset=True)
    if "unit" in payload:
        payload["unit"] = _resolve_cost_driver_unit_code(db, tenant_id, payload.get("unit"))
    for key, value in payload.items():
        setattr(driver, key, value)
    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/cost-drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost_driver(
    driver_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    driver = (
        db.query(ProductionCostDriver)
        .filter(ProductionCostDriver.id == driver_id, ProductionCostDriver.tenant_id == tenant_id)
        .first()
    )
    if not driver:
        raise HTTPException(status_code=404, detail="Cost driver no encontrado")
    db.query(RecipeCostLine).filter(RecipeCostLine.driver_id == driver_id).delete()
    db.delete(driver)
    db.commit()


# ============================================================================
# RECIPE COST LINES CRUD
# ============================================================================


@router.get("/recipes/{recipe_id}/cost-lines", response_model=list[RecipeCostLineResponse])
def list_recipe_cost_lines(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    lines = (
        db.query(RecipeCostLine)
        .filter(RecipeCostLine.recipe_id == recipe_id)
        .order_by(RecipeCostLine.line_order)
        .all()
    )
    result = []
    for line in lines:
        d = line.driver
        effective_rate = float(
            line.rate_override if line.rate_override is not None else (d.default_rate if d else 0)
        )
        line_cost = float(line.qty_standard) * effective_rate * line.headcount
        result.append(
            RecipeCostLineResponse(
                id=line.id,
                recipe_id=line.recipe_id,
                driver_id=line.driver_id,
                qty_standard=line.qty_standard,
                headcount=line.headcount,
                rate_override=line.rate_override,
                notes=line.notes,
                line_order=line.line_order,
                created_at=line.created_at,
                driver_code=d.code if d else None,
                driver_name=d.name if d else None,
                driver_unit=d.unit if d else None,
                driver_default_rate=d.default_rate if d else None,
                driver_consumption_rate=d.consumption_rate if d else None,
                effective_rate=effective_rate,
                line_cost=round(line_cost, 4),
            )
        )
    return result


@router.post(
    "/recipes/{recipe_id}/cost-lines",
    response_model=RecipeCostLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_recipe_cost_line(
    recipe_id: UUID,
    data: RecipeCostLineCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="recipe_not_found")
    line = RecipeCostLine(recipe_id=recipe_id, **data.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    d = line.driver
    effective_rate = float(
        line.rate_override if line.rate_override is not None else (d.default_rate if d else 0)
    )
    line_cost = float(line.qty_standard) * effective_rate * line.headcount
    return RecipeCostLineResponse(
        id=line.id,
        recipe_id=line.recipe_id,
        driver_id=line.driver_id,
        qty_standard=line.qty_standard,
        headcount=line.headcount,
        rate_override=line.rate_override,
        notes=line.notes,
        line_order=line.line_order,
        created_at=line.created_at,
        driver_code=d.code if d else None,
        driver_name=d.name if d else None,
        driver_unit=d.unit if d else None,
        driver_default_rate=d.default_rate if d else None,
        driver_consumption_rate=d.consumption_rate if d else None,
        effective_rate=effective_rate,
        line_cost=round(line_cost, 4),
    )


@router.put("/recipes/{recipe_id}/cost-lines/{line_id}", response_model=RecipeCostLineResponse)
def update_recipe_cost_line(
    recipe_id: UUID,
    line_id: UUID,
    data: RecipeCostLineUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    line = (
        db.query(RecipeCostLine)
        .filter(RecipeCostLine.id == line_id, RecipeCostLine.recipe_id == recipe_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Línea de costo no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(line, key, value)
    db.commit()
    db.refresh(line)
    d = line.driver
    effective_rate = float(
        line.rate_override if line.rate_override is not None else (d.default_rate if d else 0)
    )
    line_cost = float(line.qty_standard) * effective_rate * line.headcount
    return RecipeCostLineResponse(
        id=line.id,
        recipe_id=line.recipe_id,
        driver_id=line.driver_id,
        qty_standard=line.qty_standard,
        headcount=line.headcount,
        rate_override=line.rate_override,
        notes=line.notes,
        line_order=line.line_order,
        created_at=line.created_at,
        driver_code=d.code if d else None,
        driver_name=d.name if d else None,
        driver_unit=d.unit if d else None,
        driver_default_rate=d.default_rate if d else None,
        driver_consumption_rate=d.consumption_rate if d else None,
        effective_rate=effective_rate,
        line_cost=round(line_cost, 4),
    )


@router.delete("/recipes/{recipe_id}/cost-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe_cost_line(
    recipe_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    line = (
        db.query(RecipeCostLine)
        .filter(RecipeCostLine.id == line_id, RecipeCostLine.recipe_id == recipe_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Línea de costo no encontrada")
    db.delete(line)
    db.commit()


# ============================================================================
# FULL COST SUMMARY
# ============================================================================


@router.get("/recipes/{recipe_id}/full-cost", response_model=RecipeFullCostSummary)
def get_recipe_full_cost(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="recipe_not_found")
    try:
        calculate_recipe_cost(db, recipe_id)
    except Exception:
        pass
    return calculate_recipe_full_cost(db, recipe_id)


@router.post("/recipes/bulk-full-costs")
def bulk_recipe_full_costs(
    recipe_ids: list[UUID] = Body(..., embed=True),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Return full-cost summaries for multiple recipes in a single request.

    Usa bulk_calculate_recipe_full_costs: 4 queries totales sin importar
    cuántas recetas haya (vs el loop anterior que hacía N×commits).
    """
    tenant_id = UUID(claims["tenant_id"])
    return bulk_calculate_recipe_full_costs(db, recipe_ids, tenant_id)


# ============================================================================
# COST PERIODS (costeo mensual)
# ============================================================================


@router.get("/cost-periods", response_model=list[CostPeriodSummary])
def list_cost_periods(
    active_only: bool = True,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    query = db.query(CostPeriod).filter(CostPeriod.tenant_id == tenant_id)
    if active_only:
        query = query.filter(CostPeriod.is_active)
    return query.order_by(CostPeriod.month.desc()).all()


@router.post(
    "/cost-periods", response_model=CostPeriodResponse, status_code=status.HTTP_201_CREATED
)
def create_cost_period(
    data: CostPeriodCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    service = CostPeriodsService(db, tenant_id)
    existing = service.get_period(data.month)
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un período para {data.month}")
    return service.create_period(
        month=data.month,
        labor_hour_rate=data.labor_hour_rate,
        labor_paid_hours=data.labor_paid_hours,
        touch_hours_total=data.touch_hours_total,
        electricity_cost=data.electricity_cost,
        diesel_cost_month=data.diesel_cost_month,
        oven_hours_total=data.oven_hours_total,
        production_share_pct=data.production_share_pct,
        notes=data.notes,
    )


@router.get("/cost-periods/{period_id}", response_model=CostPeriodResponse)
def get_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    period = (
        db.query(CostPeriod)
        .filter(CostPeriod.id == period_id, CostPeriod.tenant_id == tenant_id)
        .first()
    )
    if not period:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    return period


@router.put("/cost-periods/{period_id}", response_model=CostPeriodResponse)
def update_cost_period(
    period_id: UUID,
    data: CostPeriodUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    service = CostPeriodsService(db, tenant_id)
    try:
        return service.update_period(period_id, **data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/cost-periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    service = CostPeriodsService(db, tenant_id)
    try:
        service.update_period(period_id, is_active=False)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cost-periods/{period_id}/validate", response_model=CostPeriodValidationResult)
def validate_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    service = CostPeriodsService(db, tenant_id)
    try:
        return service.validate_period(period_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cost-periods/{period_id}/impact")
def get_period_impact(
    period_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    service = CostPeriodsService(db, tenant_id)
    try:
        return service.get_period_impact_on_recipes(period_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cost-periods/{period_id}/close")
def close_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    service = CostPeriodsService(db, tenant_id)
    try:
        period = service.close_period(period_id)
        return {"detail": f"Período {period.month} cerrado", "closed_at": period.closed_at}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# RECIPE STEPS (etapas de receta)
# ============================================================================


@router.get("/recipes/{recipe_id}/steps", response_model=list[RecipeStepResponse])
def list_recipe_steps(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="recipe_not_found")
    return (
        db.query(RecipeStep)
        .filter(RecipeStep.recipe_id == recipe_id, RecipeStep.is_active)
        .order_by(RecipeStep.step_order)
        .all()
    )


@router.post(
    "/recipes/{recipe_id}/steps",
    response_model=RecipeStepResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recipe_step(
    recipe_id: UUID,
    data: RecipeStepCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="recipe_not_found")
    step = RecipeStep(
        recipe_id=recipe_id,
        step_name=data.step_name,
        description=data.description,
        duration_minutes=data.duration_minutes,
        is_touch=data.is_touch,
        resource_type=data.resource_type,
        actual_minutes=data.actual_minutes,
        step_order=data.step_order,
        is_active=data.is_active,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@router.put("/recipes/{recipe_id}/steps/{step_id}", response_model=RecipeStepResponse)
def update_recipe_step(
    recipe_id: UUID,
    step_id: UUID,
    data: RecipeStepUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    step = (
        db.query(RecipeStep)
        .filter(RecipeStep.id == step_id, RecipeStep.recipe_id == recipe_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(step, key, value)
    db.commit()
    db.refresh(step)
    return step


@router.delete("/recipes/{recipe_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe_step(
    recipe_id: UUID,
    step_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    step = (
        db.query(RecipeStep)
        .filter(RecipeStep.id == step_id, RecipeStep.recipe_id == recipe_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    db.delete(step)
    db.commit()
