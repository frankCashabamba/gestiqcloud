"""
Router para Recetas y desglose de costos.

Endpoints:
- GET/POST /recipes
- GET/PUT/DELETE /recipes/{recipe_id}
- GET /recipes/{recipe_id}/cost (costo completo con costos indirectos)
- POST /recipes/{recipe_id}/cost-with-period (costo para un período específico)
- GET/POST /recipes/{recipe_id}/steps (etapas de receta)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.recipes import Recipe, RecipeIngredient
from app.schemas.recipes import (
    RecipeCreate,
    RecipeDetailResponse,
    RecipeResponse,
    RecipeStepCreate,
    RecipeStepResponse,
    RecipeUpdate,
)
from app.services.recipe_calculator import calculate_recipe_cost, calculate_recipe_full_cost

router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.get("", response_model=list[RecipeResponse])
def list_recipes(
    db: Session = Depends(get_db),
    tenant_id: str = Query(..., description="Tenant ID"),
    active_only: bool = Query(True),
):
    """Lista recetas del tenant."""
    query = db.query(Recipe).filter(Recipe.tenant_id == UUID(tenant_id))
    if active_only:
        query = query.filter(Recipe.is_active == True)
    return query.all()


@router.post("", response_model=RecipeDetailResponse)
def create_recipe(
    recipe_data: RecipeCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """Crea una receta nueva."""
    recipe = Recipe(
        tenant_id=UUID(tenant_id),
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
        is_active=recipe_data.is_active,
    )
    db.add(recipe)
    db.flush()

    # Agregar ingredientes si vienen
    if recipe_data.ingredients:
        for ing_data in recipe_data.ingredients:
            ing = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=ing_data.product_id,
                qty=ing_data.qty,
                unit=ing_data.unit,
                purchase_packaging=ing_data.purchase_packaging,
                qty_per_package=ing_data.qty_per_package,
                package_unit=ing_data.package_unit,
                package_cost=ing_data.package_cost,
                notes=ing_data.notes,
                line_order=ing_data.line_order,
            )
            db.add(ing)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe(recipe_id: UUID, db: Session = Depends(get_db)):
    """Obtiene detalle de una receta."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.put("/{recipe_id}", response_model=RecipeDetailResponse)
def update_recipe(
    recipe_id: UUID,
    recipe_data: RecipeUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza una receta."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Actualizar campos
    for key, value in recipe_data.model_dump(exclude_unset=True, exclude={"ingredients"}).items():
        if value is not None:
            setattr(recipe, key, value)

    # Actualizar ingredientes si se proporciona
    if recipe_data.ingredients is not None:
        # Eliminar existentes
        db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()

        # Agregar nuevos
        for ing_data in recipe_data.ingredients:
            ing = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=ing_data.product_id,
                qty=ing_data.qty,
                unit=ing_data.unit,
                purchase_packaging=ing_data.purchase_packaging,
                qty_per_package=ing_data.qty_per_package,
                package_unit=ing_data.package_unit,
                package_cost=ing_data.package_cost,
                notes=ing_data.notes,
                line_order=ing_data.line_order,
            )
            db.add(ing)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: UUID, db: Session = Depends(get_db)):
    """Elimina una receta."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    db.delete(recipe)
    db.commit()
    return {"detail": "Recipe deleted"}


# ============================================================================
# CÁLCULOS DE COSTO
# ============================================================================


@router.get("/{recipe_id}/cost")
def get_recipe_cost_breakdown(recipe_id: UUID, db: Session = Depends(get_db)):
    """
    Obtiene desglose de costo de receta (solo ingredientes).
    """
    try:
        result = calculate_recipe_cost(db, recipe_id, update_product_price=False)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{recipe_id}/full-cost")
def get_recipe_full_cost(
    recipe_id: UUID,
    period_month: str | None = Query(None, description="Período YYYY-MM para usar CostPeriod"),
    db: Session = Depends(get_db),
):
    """
    Obtiene costo completo: materiales + mano de obra + indirectos.
    
    Si period_month se proporciona (ej: 2025-02), usa datos reales de ese mes.
    Si no, usa fórmulas simplificadas.
    
    Respuesta incluye desglose por categoría y labor_burden_factor.
    """
    try:
        result = calculate_recipe_full_cost(db, recipe_id, period_month=period_month)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# RECIPE STEPS (ETAPAS)
# ============================================================================


@router.get("/{recipe_id}/steps", response_model=list[RecipeStepResponse])
def list_recipe_steps(recipe_id: UUID, db: Session = Depends(get_db)):
    """Lista etapas de una receta."""
    from app.models.production._recipe_steps import RecipeStep

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    steps = (
        db.query(RecipeStep)
        .filter(RecipeStep.recipe_id == recipe_id, RecipeStep.is_active == True)
        .order_by(RecipeStep.step_order)
        .all()
    )
    return steps


@router.post("/{recipe_id}/steps", response_model=RecipeStepResponse)
def create_recipe_step(
    recipe_id: UUID,
    step_data: RecipeStepCreate,
    db: Session = Depends(get_db),
):
    """Crea una etapa en una receta."""
    from app.models.production._recipe_steps import RecipeStep

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    step = RecipeStep(
        recipe_id=recipe_id,
        step_name=step_data.step_name,
        description=step_data.description,
        duration_minutes=step_data.duration_minutes,
        is_touch=step_data.is_touch,
        resource_type=step_data.resource_type,
        actual_minutes=step_data.actual_minutes,
        step_order=step_data.step_order,
        is_active=step_data.is_active,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@router.get("/{recipe_id}/steps/{step_id}", response_model=RecipeStepResponse)
def get_recipe_step(recipe_id: UUID, step_id: UUID, db: Session = Depends(get_db)):
    """Obtiene una etapa específica."""
    from app.models.production._recipe_steps import RecipeStep

    step = (
        db.query(RecipeStep)
        .filter(RecipeStep.id == step_id, RecipeStep.recipe_id == recipe_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return step


@router.put("/{recipe_id}/steps/{step_id}", response_model=RecipeStepResponse)
def update_recipe_step(
    recipe_id: UUID,
    step_id: UUID,
    step_data: RecipeStepCreate,
    db: Session = Depends(get_db),
):
    """Actualiza una etapa."""
    from app.models.production._recipe_steps import RecipeStep

    step = (
        db.query(RecipeStep)
        .filter(RecipeStep.id == step_id, RecipeStep.recipe_id == recipe_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    for key, value in step_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(step, key, value)

    db.commit()
    db.refresh(step)
    return step


@router.delete("/{recipe_id}/steps/{step_id}")
def delete_recipe_step(recipe_id: UUID, step_id: UUID, db: Session = Depends(get_db)):
    """Elimina una etapa."""
    from app.models.production._recipe_steps import RecipeStep

    step = (
        db.query(RecipeStep)
        .filter(RecipeStep.id == step_id, RecipeStep.recipe_id == recipe_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    db.delete(step)
    db.commit()
    return {"detail": "Step deleted"}
