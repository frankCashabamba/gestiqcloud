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

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

from app.models.production.production_order import ProductionOrder, ProductionOrderLine
from app.models.recipes import Recipe, RecipeIngredient
from app.models.inventory.stock import StockItem, StockMove
from app.schemas.production import (
    ProductionOrderCreate,
    ProductionOrderUpdate,
    ProductionOrderResponse,
    ProductionOrderList,
    ProductionOrderStartRequest,
    ProductionOrderCompleteRequest,
    ProductionOrderStats,
    ProductionCalculatorRequest,
    ProductionCalculatorResponse,
    IngredientRequirement,
)
from app.schemas.recipes import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeDetailResponse,
    RecipeIngredientCreate,
    RecipeIngredientUpdate,
    RecipeIngredientResponse,
    RecipeCostBreakdownResponse,
    ProductionCalculationRequest,
    ProductionCalculationResponse,
    PurchaseOrderRequest,
    PurchaseOrderResponse,
    RecipeProfitabilityRequest,
    RecipeProfitabilityResponse,
    RecipeComparisonResponse,
)
from app.services.recipe_calculator import (
    calculate_recipe_cost,
    calculate_purchase_for_production,
    calculate_production_time,
    create_purchase_order_from_recipe,
    compare_recipe_costs,
    get_recipe_profitability,
)


router = APIRouter(
    prefix="/production",
    tags=["Production"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# HELPERS
def _generate_next_numero(db: Session, tenant_id: UUID) -> str:
    year = datetime.utcnow().year
    prefix = f"OP-{year}-"
    stmt = select(ProductionOrder).where(
        ProductionOrder.tenant_id == tenant_id,
        ProductionOrder.numero.like(f"{prefix}%")
    ).order_by(ProductionOrder.numero.desc()).limit(1)
    result = db.execute(stmt)
    last_order = result.scalar_one_or_none()
    if last_order and last_order.numero:
        try:
            last_num = int(last_order.numero.split('-')[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}{next_num:04d}"


def _generate_batch_number(db: Session, tenant_id: UUID) -> str:
    year = datetime.utcnow().year
    month = datetime.utcnow().month
    prefix = f"LOT-{year}{month:02d}-"
    stmt = select(ProductionOrder).where(
        ProductionOrder.tenant_id == tenant_id,
        ProductionOrder.batch_number.like(f"{prefix}%")
    ).order_by(ProductionOrder.batch_number.desc()).limit(1)
    result = db.execute(stmt)
    last_order = result.scalar_one_or_none()
    if last_order and last_order.batch_number:
        try:
            last_num = int(last_order.batch_number.split('-')[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}{next_num:04d}"


async def _create_stock_moves_for_ingredients(
    db: Session,
    order: ProductionOrder,
    warehouse_id: Optional[UUID] = None
) -> List[UUID]:
    stock_move_ids = []
    for line in order.lines:
        stock_move = StockMove(
            tenant_id=order.tenant_id,
            kind="production_consume",
            product_id=line.ingredient_product_id,
            qty=-abs(float(line.qty_consumed)),
            warehouse_id=warehouse_id,
            ref_doc_type="production_order",
            ref_doc_id=order.id,
            posted_at=datetime.utcnow(),
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
            stock_item.qty_on_hand -= abs(float(line.qty_consumed))
        else:
            new_stock_item = StockItem(
                tenant_id=order.tenant_id,
                product_id=line.ingredient_product_id,
                warehouse_id=warehouse_id,
                qty_on_hand=-abs(float(line.qty_consumed)),
            )
            db.add(new_stock_item)
    return stock_move_ids


async def _create_stock_move_for_output(
    db: Session,
    order: ProductionOrder,
    warehouse_id: Optional[UUID] = None
) -> UUID:
    stock_move = StockMove(
        tenant_id=order.tenant_id,
        kind="production_output",
        product_id=order.product_id,
        qty=abs(float(order.qty_produced)),
        warehouse_id=warehouse_id,
        ref_doc_type="production_order",
        ref_doc_id=order.id,
        posted_at=datetime.utcnow(),
    )
    db.add(stock_move)
    db.flush()
    stmt = select(StockItem).where(
        StockItem.tenant_id == order.tenant_id,
        StockItem.product_id == order.product_id,
    )
    if warehouse_id:
        stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
    result = db.execute(stmt)
    stock_item = result.scalar_one_or_none()
    if stock_item:
        stock_item.qty_on_hand += abs(float(order.qty_produced))
        if order.batch_number:
            stock_item.lot = order.batch_number
    else:
        new_stock_item = StockItem(
            tenant_id=order.tenant_id,
            product_id=order.product_id,
            warehouse_id=warehouse_id,
            qty_on_hand=abs(float(order.qty_produced)),
            lot=order.batch_number,
        )
        db.add(new_stock_item)
    return stock_move.id


# ÓRDENES DE PRODUCCIÓN
@router.get("/orders", response_model=ProductionOrderList)
async def list_production_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    recipe_id: Optional[UUID] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
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
    query = query.order_by(ProductionOrder.created_at.desc())
    count_query = select(func.count()).select_from(query.subquery())
    total_result = db.execute(count_query)
    total = total_result.scalar() or 0
    result = db.execute(query.offset(skip).limit(limit))
    orders = result.scalars().all()
    return ProductionOrderList(items=orders, total=total, skip=skip, limit=limit)


@router.post("/orders", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_production_order(
    order_in: ProductionOrderCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])
    recipe_stmt = select(Recipe).where(Recipe.id == order_in.recipe_id)
    recipe_result = db.execute(recipe_stmt)
    recipe = recipe_result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
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
        rendimiento = float(recipe.rendimiento) if recipe.rendimiento else 1.0
        scale_factor = float(order_in.qty_planned) / rendimiento if rendimiento > 0 else 1.0
        for ing in ingredients:
            qty_required = float(ing.qty) * scale_factor
            line = ProductionOrderLine(
                order_id=order.id,
                ingredient_product_id=ing.producto_id,
                qty_required=Decimal(str(qty_required)),
                qty_consumed=Decimal("0"),
                unit=ing.unidad_medida or "unit",
                cost_unit=ing.costo_presentacion or Decimal("0"),
            )
            line.cost_total = line.qty_required * line.cost_unit
            db.add(line)
    db.commit()
    db.refresh(order)
    return order


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada")
    if order.status not in ["DRAFT", "SCHEDULED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede editar orden en estado {order.status}"
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada")
    if order.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar órdenes en estado DRAFT"
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada")
    if order.status not in ["DRAFT", "SCHEDULED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede iniciar orden en estado {order.status}"
        )
    order.status = "IN_PROGRESS"
    order.started_at = request.started_at or datetime.utcnow()
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
    stmt = select(ProductionOrder).where(
        ProductionOrder.id == order_id,
        ProductionOrder.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada")
    if order.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden completar órdenes en estado IN_PROGRESS (actual: {order.status})"
        )
    order.qty_produced = request.qty_produced
    order.waste_qty = request.waste_qty
    order.waste_reason = request.waste_reason
    order.completed_at = request.completed_at or datetime.utcnow()
    order.status = "COMPLETED"
    if not order.batch_number:
        order.batch_number = request.batch_number or _generate_batch_number(db, tenant_id)
    if request.notes:
        order.notes = (order.notes or "") + f"\n[Completado] {request.notes}"
    for line in order.lines:
        if not line.qty_consumed or line.qty_consumed == 0:
            line.qty_consumed = line.qty_required
    try:
        await _create_stock_moves_for_ingredients(db, order, order.warehouse_id)
        await _create_stock_move_for_output(db, order, order.warehouse_id)
        db.commit()
        db.refresh(order)
        return order
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear movimientos de stock: {str(e)}"
        )


@router.post("/orders/{order_id}/cancel", response_model=ProductionOrderResponse)
async def cancel_production(
    order_id: UUID,
    reason: Optional[str] = Query(None),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de producción no encontrada")
    if order.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar una orden completada"
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
    recipe_stmt = select(Recipe).where(Recipe.id == request.recipe_id)
    recipe_result = db.execute(recipe_stmt)
    recipe = recipe_result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    ingredients_stmt = select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    ingredients_result = db.execute(ingredients_stmt)
    ingredients = ingredients_result.scalars().all()
    rendimiento = float(recipe.rendimiento) if recipe.rendimiento else 1.0
    scale_factor = float(request.qty_desired) / rendimiento if rendimiento > 0 else 1.0
    all_ingredients = []
    missing_ingredients = []
    total_cost = Decimal("0")
    can_produce = True
    for ing in ingredients:
        qty_required = Decimal(str(float(ing.qty) * scale_factor))
        stock_stmt = select(func.sum(StockItem.qty_on_hand)).where(
            StockItem.tenant_id == tenant_id,
            StockItem.product_id == ing.producto_id,
        )
        stock_result = db.execute(stock_stmt)
        stock_available = stock_result.scalar() or Decimal("0")
        stock_sufficient = stock_available >= qty_required
        qty_to_purchase = max(Decimal("0"), qty_required - stock_available)
        cost_unit = ing.costo_presentacion or Decimal("0")
        total_cost += qty_required * cost_unit
        ingredient_req = IngredientRequirement(
            ingredient_id=ing.producto_id,
            ingredient_name=ing.producto_id,
            qty_required=qty_required,
            unit=ing.unidad_medida or "unit",
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
        min_ratio = float('inf')
        for ing_data in ingredients:
            stock_stmt = select(func.sum(StockItem.qty_on_hand)).where(
                StockItem.tenant_id == tenant_id,
                StockItem.product_id == ing_data.producto_id,
            )
            stock_result = db.execute(stock_stmt)
            stock_qty = float(stock_result.scalar() or 0)
            ing_qty_per_unit = float(ing_data.qty) / rendimiento if rendimiento > 0 else 0
            if ing_qty_per_unit > 0:
                ratio = stock_qty / ing_qty_per_unit
                min_ratio = min(min_ratio, ratio)
        qty_producible = Decimal(str(min_ratio)) if min_ratio != float('inf') else Decimal("0")
    return ProductionCalculatorResponse(
        recipe_id=recipe.id,
        recipe_name=recipe.name or "Sin nombre",
        qty_desired=request.qty_desired,
        qty_producible=qty_producible,
        can_produce=can_produce,
        missing_ingredients=missing_ingredients,
        all_ingredients=all_ingredients,
        estimated_cost=total_cost,
        production_time_minutes=recipe.tiempo_preparacion,
    )


@router.get("/stats", response_model=ProductionOrderStats)
async def get_production_stats(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
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
@router.get("/recipes", response_model=List[RecipeResponse])
def list_recipes(
    activo: Optional[bool] = None,
    product_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    query = db.query(Recipe)
    if activo is not None:
        query = query.filter(Recipe.activo == activo)
    if product_id:
        query = query.filter(Recipe.product_id == product_id)
    recipes = query.offset(skip).limit(limit).all()
    return recipes


@router.post("/recipes", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    recipe_data: RecipeCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    recipe = Recipe(
        product_id=recipe_data.product_id,
        name=recipe_data.name or recipe_data.nombre,
        rendimiento=recipe_data.rendimiento,
        tiempo_preparacion=recipe_data.tiempo_preparacion,
        instrucciones=recipe_data.instrucciones,
        activo=recipe_data.activo if recipe_data.activo is not None else True,
        costo_total=0,
    )
    db.add(recipe)
    db.flush()
    if recipe_data.ingredientes:
        for idx, ing_data in enumerate(recipe_data.ingredientes):
            ingrediente = RecipeIngredient(
                recipe_id=recipe.id,
                producto_id=ing_data.producto_id,
                qty=ing_data.qty,
                unidad_medida=ing_data.unidad_medida,
                presentacion_compra=ing_data.presentacion_compra,
                qty_presentacion=ing_data.qty_presentacion,
                unidad_presentacion=ing_data.unidad_presentacion,
                costo_presentacion=ing_data.costo_presentacion,
                notas=ing_data.notas,
                orden=ing_data.orden if ing_data.orden is not None else idx,
            )
            db.add(ingrediente)
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
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return recipe


@router.put("/recipes/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: UUID,
    recipe_data: RecipeUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    update_data = recipe_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(recipe, key, value)
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
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
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
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")

    duplicate = (
        db.query(RecipeIngredient)
        .filter(
            RecipeIngredient.recipe_id == recipe_id,
            RecipeIngredient.producto_id == payload.producto_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ingrediente ya existe en la receta",
        )

    next_order = payload.orden
    if next_order is None:
        current_max = (
            db.query(func.max(RecipeIngredient.orden))
            .filter(RecipeIngredient.recipe_id == recipe_id)
            .scalar()
        )
        next_order = (current_max or 0) + 1

    ingrediente = RecipeIngredient(
        recipe_id=recipe_id,
        producto_id=payload.producto_id,
        qty=payload.qty,
        unidad_medida=payload.unidad_medida,
        presentacion_compra=payload.presentacion_compra,
        qty_presentacion=payload.qty_presentacion,
        unidad_presentacion=payload.unidad_presentacion,
        costo_presentacion=payload.costo_presentacion,
        notas=payload.notas,
        orden=next_order,
    )
    db.add(ingrediente)
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
    if "producto_id" in data:
        duplicate = (
            db.query(RecipeIngredient)
            .filter(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.producto_id == data["producto_id"],
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
        return calculate_recipe_cost(db, recipe_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")


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
        calculation = calculate_purchase_for_production(
            db, recipe_id, payload.qty_to_produce
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")

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
    recipe_ids: List[UUID] = Body(..., min_length=1),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    comparisons = compare_recipe_costs(db, recipe_ids)
    for item in comparisons:
        nombre = item.get("nombre")
        if "name" not in item and nombre is not None:
            item["name"] = nombre

    return {"recipes": comparisons}
