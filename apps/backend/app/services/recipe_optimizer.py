from __future__ import annotations

import json
import logging
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.core.products import Product
from app.models.production._cost_drivers import ProductionCostDriver, RecipeCostLine
from app.models.production._cost_periods import CostPeriod
from app.models.recipes import Recipe, RecipeIngredient
from app.schemas.recipes import (
    RecipeIngredientCreate,
    RecipeOptimizationChange,
    RecipeOptimizationCostSnapshot,
    RecipeOptimizationDraft,
    RecipeOptimizationIngredientDraft,
    RecipeOptimizationRequest,
    RecipeOptimizationResponse,
)
from app.services.ai.base import AITask
from app.services.ai.service import AIService
from app.services.recipe_calculator import (
    _compute_full_cost_from_objects,
    calculate_recipe_full_cost,
)
from app.shared.utils import safe_decimal as _safe_decimal
from app.utils.unit_converter import convert, normalize_unit_name

logger = logging.getLogger(__name__)


def _normalize_text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_json_payload(raw: str) -> dict:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("La IA no devolvio contenido")

    if text.startswith("```"):
        parts = text.split("```")
        fenced = next((part for part in parts if "{" in part and "}" in part), text)
        text = fenced.replace("json", "", 1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("La respuesta de IA no es JSON valido") from None


def _convert_qty_to_package_unit(qty: object, unit: object, package_unit: object) -> Decimal:
    qty_decimal = _safe_decimal(qty)
    unit_code = normalize_unit_name(str(unit or ""))
    package_unit_code = normalize_unit_name(str(package_unit or unit_code))
    if not unit_code or not package_unit_code:
        return qty_decimal
    if unit_code.lower() == package_unit_code.lower():
        return qty_decimal
    try:
        return Decimal(str(convert(float(qty_decimal), unit_code, package_unit_code)))
    except Exception:
        return qty_decimal


def _estimate_ingredient_cost(ingredient: RecipeIngredient | SimpleNamespace) -> Decimal:
    qty_in_package_unit = _convert_qty_to_package_unit(
        getattr(ingredient, "qty", 0),
        getattr(ingredient, "unit", ""),
        getattr(ingredient, "package_unit", getattr(ingredient, "unit", "")),
    )
    qty_per_package = max(
        _safe_decimal(getattr(ingredient, "qty_per_package", 0)),
        Decimal("0.0001"),
    )
    package_cost = max(_safe_decimal(getattr(ingredient, "package_cost", 0)), Decimal("0"))
    return (qty_in_package_unit / qty_per_package) * package_cost


def _load_recipe_cost_context(
    db: Session,
    tenant_id: UUID,
    recipe_id: UUID,
) -> tuple[CostPeriod | None, list[RecipeCostLine], list[ProductionCostDriver]]:
    cost_period = None
    cost_lines: list[RecipeCostLine] = []
    active_drivers: list[ProductionCostDriver] = []

    try:
        cost_period = (
            db.query(CostPeriod)
            .filter(CostPeriod.tenant_id == tenant_id, CostPeriod.is_active)
            .order_by(CostPeriod.month.desc())
            .first()
        )
    except Exception:
        logger.debug("CostPeriod no disponible para optimizacion", exc_info=True)
        db.rollback()

    try:
        cost_lines = (
            db.query(RecipeCostLine)
            .filter(RecipeCostLine.recipe_id == recipe_id)
            .options(joinedload(RecipeCostLine.driver))
            .order_by(RecipeCostLine.line_order)
            .all()
        )
    except Exception:
        logger.debug("RecipeCostLine no disponible para optimizacion", exc_info=True)
        db.rollback()

    try:
        active_drivers = (
            db.query(ProductionCostDriver)
            .filter(
                ProductionCostDriver.tenant_id == tenant_id,
                ProductionCostDriver.is_active.is_(True),
            )
            .all()
        )
    except Exception:
        logger.debug("ProductionCostDriver no disponible para optimizacion", exc_info=True)
        db.rollback()

    return cost_period, cost_lines, active_drivers


def _compute_margin_pct(selling_price: float | None, full_cost_unit: float) -> float | None:
    if selling_price is None or selling_price <= 0:
        return None
    return round(((selling_price - full_cost_unit) / selling_price) * 100, 2)


def _build_cost_snapshot(
    *,
    yield_qty: int,
    materials_total: float,
    full_cost_total: float,
    full_cost_unit: float,
    selling_price: float | None,
) -> RecipeOptimizationCostSnapshot:
    return RecipeOptimizationCostSnapshot(
        yield_qty=yield_qty,
        materials_total=round(float(materials_total), 4),
        full_cost_total=round(float(full_cost_total), 4),
        full_cost_unit=round(float(full_cost_unit), 4),
        selling_price=round(float(selling_price), 4) if selling_price is not None else None,
        margin_pct=_compute_margin_pct(selling_price, float(full_cost_unit)),
    )


def _build_prompt(
    *,
    recipe: Recipe,
    product: Product | None,
    ingredients: list[RecipeIngredient],
    request: RecipeOptimizationRequest,
    current_cost: dict,
    selling_price: float | None,
) -> str:
    locked_ids = {str(pid) for pid in request.locked_product_ids}
    ingredient_rows = []
    for ingredient in ingredients:
        ingredient_rows.append(
            {
                "product_id": str(ingredient.product_id),
                "product_name": ingredient.product.name if ingredient.product else "Ingrediente",
                "qty": float(ingredient.qty or 0),
                "unit": ingredient.unit,
                "estimated_cost": round(float(_estimate_ingredient_cost(ingredient)), 4),
                "purchase_packaging": ingredient.purchase_packaging,
                "qty_per_package": float(ingredient.qty_per_package or 0),
                "package_unit": ingredient.package_unit,
                "package_cost": float(ingredient.package_cost or 0),
                "locked": str(ingredient.product_id) in locked_ids,
                "notes": ingredient.notes,
            }
        )

    current_summary = {
        "recipe_name": recipe.name,
        "product_name": product.name if product else None,
        "yield_qty": recipe.yield_qty,
        "materials_total": current_cost.get("materials_total"),
        "full_cost_total": current_cost.get("full_cost_total"),
        "full_cost_unit": current_cost.get("full_cost_unit"),
        "selling_price": selling_price,
        "current_margin_pct": _compute_margin_pct(
            selling_price, current_cost.get("full_cost_unit", 0)
        ),
        "target_margin_pct": request.target_margin_pct,
        "production_params": {
            "prep_time_minutes": recipe.prep_time_minutes,
            "baking_time_minutes": recipe.baking_time_minutes,
            "oven_temp_celsius": recipe.oven_temp_celsius,
            "rest_time_minutes": recipe.rest_time_minutes,
            "touch_minutes_standard": recipe.touch_minutes_standard,
            "oven_minutes_standard": recipe.oven_minutes_standard,
            "process_minutes": recipe.process_minutes,
            "waste_pct": float(recipe.waste_pct or 0),
            "overhead_pct": float(recipe.overhead_pct or 0),
        },
    }

    return f"""
Eres un tecnologo de alimentos y analista de costes.
Objetivo: optimizar una receta reduciendo coste sin degradar calidad percibida.

Reglas obligatorias:
1. Devuelve SOLO JSON valido.
2. Solo puedes usar los ingredient_product_id listados. No inventes ingredientes nuevos.
3. Respeta yield_qty salvo que sea imprescindible; si lo cambias, justificalo.
4. No cambies ingredientes bloqueados.
5. Si no ves una mejora razonable, deja cantidades iguales y explicalo.
6. Limita cambios significativos a un maximo de {request.max_ingredients_to_change} ingredientes.
7. Prioriza pequenos ajustes de gramaje, merma y proceso antes que cambios agresivos.

Receta actual:
{json.dumps(current_summary, ensure_ascii=True, indent=2)}

Ingredientes actuales:
{json.dumps(ingredient_rows, ensure_ascii=True, indent=2)}

Restricciones del operador:
{request.constraints or "Sin restricciones adicionales"}

Formato JSON requerido:
{{
  "summary": "resumen ejecutivo corto",
  "assumptions": ["..."],
  "warnings": ["..."],
  "yield_qty": 100,
  "prep_time_minutes": 0,
  "baking_time_minutes": 0,
  "oven_temp_celsius": 0,
  "rest_time_minutes": 0,
  "touch_minutes_standard": 0,
  "oven_minutes_standard": 0,
  "process_minutes": 0,
  "waste_pct": 0,
  "overhead_pct": 0,
  "instructions": "texto opcional",
  "ingredients": [
    {{
      "product_id": "uuid existente",
      "qty": 0,
      "reason": "por que cambia o se mantiene"
    }}
  ]
}}
""".strip()


async def optimize_recipe_with_ai(
    *,
    db: Session,
    tenant_id: UUID,
    user_id: str | None,
    recipe_id: UUID,
    request: RecipeOptimizationRequest,
) -> RecipeOptimizationResponse:
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.tenant_id == tenant_id).first()
    if not recipe:
        raise ValueError("recipe_not_found")

    ingredients = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .options(joinedload(RecipeIngredient.product))
        .order_by(RecipeIngredient.line_order, RecipeIngredient.created_at)
        .all()
    )
    if not ingredients:
        raise ValueError("recipe_has_no_ingredients")

    product = db.query(Product).filter(Product.id == recipe.product_id).first()
    selling_price = (
        request.selling_price
        if request.selling_price is not None
        else (float(product.price) if product and product.price is not None else None)
    )

    try:
        current_cost = calculate_recipe_full_cost(db, recipe_id)
    except Exception:
        logger.debug("Fallo full cost actual; usando fallback basico", exc_info=True)
        db.rollback()
        base_total = float(recipe.total_cost or 0)
        base_unit = base_total / max(int(recipe.yield_qty or 1), 1)
        current_cost = {
            "yield_qty": int(recipe.yield_qty or 1),
            "materials_total": base_total,
            "full_cost_total": base_total,
            "full_cost_unit": base_unit,
        }
    prompt = _build_prompt(
        recipe=recipe,
        product=product,
        ingredients=ingredients,
        request=request,
        current_cost=current_cost,
        selling_price=selling_price,
    )

    ai_response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt=prompt,
        temperature=0.2,
        max_tokens=2200,
        db=db,
        tenant_id=str(tenant_id),
        module="production_recipe_optimization",
        user_id=user_id,
    )
    if ai_response.is_error:
        raise ValueError(ai_response.error or "ai_optimization_failed")

    ai_payload = _extract_json_payload(ai_response.content)
    raw_ingredients = ai_payload.get("ingredients")
    if not isinstance(raw_ingredients, list) or not raw_ingredients:
        raise ValueError("La IA no devolvio ingredientes optimizados")

    ai_by_id = {
        str(item.get("product_id")): item
        for item in raw_ingredients
        if isinstance(item, dict) and item.get("product_id")
    }
    locked_ids = {str(pid) for pid in request.locked_product_ids}
    warnings = _normalize_text_list(ai_payload.get("warnings"))
    seen_product_ids: set[str] = set()
    duplicate_product_names: list[str] = []
    for ingredient in ingredients:
        ingredient_id = str(ingredient.product_id)
        if ingredient_id in seen_product_ids:
            duplicate_product_names.append(
                ingredient.product.name if ingredient.product else ingredient_id
            )
            continue
        seen_product_ids.add(ingredient_id)
    if duplicate_product_names:
        duplicates_text = ", ".join(dict.fromkeys(duplicate_product_names))
        warnings.append(
            "La receta contiene ingredientes repetidos por producto "
            f"({duplicates_text}); la propuesta se mantiene por linea para no perder trazabilidad."
        )
    optimized_models: list[SimpleNamespace] = []
    changed_count = 0

    for idx, ingredient in enumerate(ingredients):
        ingredient_id = str(ingredient.product_id)
        ai_item = ai_by_id.get(ingredient_id, {})
        current_qty = _safe_decimal(ingredient.qty)
        suggested_qty = _safe_decimal(ai_item.get("qty"), current_qty)

        if ingredient_id in locked_ids:
            if suggested_qty != current_qty:
                warnings.append(
                    f"Se mantuvo fijo {ingredient.product.name if ingredient.product else ingredient_id} por bloqueo del operador."
                )
            suggested_qty = current_qty
            change_type = "locked"
        else:
            if suggested_qty <= 0:
                warnings.append(
                    f"La IA devolvio una cantidad no valida para {ingredient.product.name if ingredient.product else ingredient_id}; se conserva la actual."
                )
                suggested_qty = current_qty
            change_type = (
                "adjust_qty" if abs(suggested_qty - current_qty) > Decimal("0.0001") else "keep"
            )

        changed = change_type == "adjust_qty"
        if changed:
            changed_count += 1

        optimized_models.append(
            SimpleNamespace(
                product_id=ingredient.product_id,
                qty=suggested_qty,
                unit=ingredient.unit,
                purchase_packaging=ingredient.purchase_packaging,
                qty_per_package=ingredient.qty_per_package,
                package_unit=ingredient.package_unit,
                package_cost=ingredient.package_cost,
                notes=ingredient.notes,
                line_order=(
                    int(ingredient.line_order)
                    if getattr(ingredient, "line_order", None) is not None
                    else idx
                ),
                product_name=ingredient.product.name if ingredient.product else "Ingrediente",
                reason=str(ai_item.get("reason") or "").strip() or None,
                original_qty=current_qty,
                original_cost=_estimate_ingredient_cost(ingredient),
                changed=changed,
                locked=ingredient_id in locked_ids,
            )
        )

    max_changes = max(int(request.max_ingredients_to_change or 0), 0)
    if changed_count > max_changes > 0:
        warnings.append(
            f"La IA propuso {changed_count} cambios de ingredientes; se conservan solo los primeros {max_changes} para respetar el limite."
        )
        applied_changes = 0
        limited_models: list[SimpleNamespace] = []
        for item in optimized_models:
            if item.changed:
                applied_changes += 1
                if applied_changes > max_changes:
                    item = SimpleNamespace(
                        **{
                            **item.__dict__,
                            "qty": item.original_qty,
                            "changed": False,
                            "reason": "Cambio descartado por limite operativo",
                        }
                    )
            limited_models.append(item)
        optimized_models = limited_models
        changed_count = sum(1 for item in optimized_models if item.changed)

    optimized_materials_total = sum(_estimate_ingredient_cost(item) for item in optimized_models)

    yield_qty = max(int(ai_payload.get("yield_qty") or recipe.yield_qty or 1), 1)
    draft_recipe = SimpleNamespace(
        id=recipe.id,
        name=recipe.name,
        yield_qty=yield_qty,
        total_cost=optimized_materials_total,
        prep_time_minutes=int(ai_payload.get("prep_time_minutes") or recipe.prep_time_minutes or 0)
        or None,
        baking_time_minutes=int(
            ai_payload.get("baking_time_minutes") or recipe.baking_time_minutes or 0
        )
        or None,
        oven_temp_celsius=int(ai_payload.get("oven_temp_celsius") or recipe.oven_temp_celsius or 0)
        or None,
        rest_time_minutes=int(ai_payload.get("rest_time_minutes") or recipe.rest_time_minutes or 0)
        or None,
        touch_minutes_standard=int(
            ai_payload.get("touch_minutes_standard") or recipe.touch_minutes_standard or 0
        )
        or 0,
        oven_minutes_standard=int(
            ai_payload.get("oven_minutes_standard") or recipe.oven_minutes_standard or 0
        )
        or 0,
        process_minutes=int(ai_payload.get("process_minutes") or recipe.process_minutes or 0)
        or None,
        waste_pct=float(
            ai_payload.get("waste_pct")
            if ai_payload.get("waste_pct") is not None
            else float(recipe.waste_pct or 0)
        ),
        overhead_pct=float(
            ai_payload.get("overhead_pct")
            if ai_payload.get("overhead_pct") is not None
            else float(recipe.overhead_pct or 0)
        ),
        trays_per_batch=recipe.trays_per_batch,
        units_per_tray=recipe.units_per_tray,
    )

    cost_period, cost_lines, active_drivers = _load_recipe_cost_context(db, tenant_id, recipe_id)
    try:
        optimized_cost = _compute_full_cost_from_objects(
            recipe=draft_recipe,
            cost_period=cost_period,
            cost_lines=cost_lines,
            active_drivers=active_drivers,
        )
    except Exception:
        logger.debug("Fallo full cost optimizado; usando fallback basico", exc_info=True)
        optimized_total = float(optimized_materials_total)
        optimized_cost = {
            "yield_qty": yield_qty,
            "materials_total": optimized_total,
            "full_cost_total": optimized_total,
            "full_cost_unit": optimized_total / max(yield_qty, 1),
        }

    current_snapshot = _build_cost_snapshot(
        yield_qty=int(current_cost.get("yield_qty") or recipe.yield_qty or 1),
        materials_total=float(current_cost.get("materials_total") or 0),
        full_cost_total=float(current_cost.get("full_cost_total") or 0),
        full_cost_unit=float(current_cost.get("full_cost_unit") or 0),
        selling_price=selling_price,
    )
    optimized_snapshot = _build_cost_snapshot(
        yield_qty=int(optimized_cost.get("yield_qty") or yield_qty),
        materials_total=float(optimized_cost.get("materials_total") or 0),
        full_cost_total=float(optimized_cost.get("full_cost_total") or 0),
        full_cost_unit=float(optimized_cost.get("full_cost_unit") or 0),
        selling_price=selling_price,
    )

    changes: list[RecipeOptimizationChange] = []
    optimized_ingredients: list[RecipeOptimizationIngredientDraft] = []
    draft_ingredients: list[RecipeIngredientCreate] = []
    for item in optimized_models:
        current_cost_item = float(item.original_cost)
        optimized_cost_item = float(_estimate_ingredient_cost(item))
        change_type = "locked" if item.locked else ("adjust_qty" if item.changed else "keep")
        changes.append(
            RecipeOptimizationChange(
                product_id=item.product_id,
                product_name=item.product_name,
                line_order=int(item.line_order or 0),
                change_type=change_type,
                current_qty=round(float(item.original_qty or 0), 4),
                suggested_qty=round(float(item.qty or 0), 4),
                unit=item.unit,
                estimated_cost_delta=round(optimized_cost_item - current_cost_item, 4),
                rationale=item.reason,
            )
        )
        optimized_ingredients.append(
            RecipeOptimizationIngredientDraft(
                product_id=item.product_id,
                product_name=item.product_name,
                qty=round(float(item.qty or 0), 4),
                unit=item.unit,
                purchase_packaging=str(item.purchase_packaging or ""),
                qty_per_package=round(float(item.qty_per_package or 0), 4),
                package_unit=item.package_unit,
                package_cost=round(float(item.package_cost or 0), 4),
                notes=item.notes,
                line_order=int(item.line_order or 0),
                estimated_cost=round(optimized_cost_item, 4),
                locked=bool(item.locked),
                changed=bool(item.changed),
                reason=item.reason,
            )
        )
        draft_ingredients.append(
            RecipeIngredientCreate(
                product_id=item.product_id,
                qty=round(float(item.qty or 0), 4),
                unit=item.unit,
                purchase_packaging=str(item.purchase_packaging or "-"),
                qty_per_package=max(round(float(item.qty_per_package or 1), 4), 0.0001),
                package_unit=item.package_unit,
                package_cost=max(round(float(item.package_cost or 0), 4), 0),
                notes=item.notes,
                line_order=int(item.line_order or 0),
            )
        )

    savings_total = round(
        float(current_snapshot.full_cost_total - optimized_snapshot.full_cost_total),
        4,
    )
    savings_unit = round(
        float(current_snapshot.full_cost_unit - optimized_snapshot.full_cost_unit),
        4,
    )
    savings_pct = round(
        (
            ((savings_total / current_snapshot.full_cost_total) * 100)
            if current_snapshot.full_cost_total > 0
            else 0
        ),
        2,
    )

    return RecipeOptimizationResponse(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        summary=str(ai_payload.get("summary") or "Propuesta generada sin resumen de IA.").strip(),
        assumptions=_normalize_text_list(ai_payload.get("assumptions")),
        warnings=warnings,
        current=current_snapshot,
        optimized=optimized_snapshot,
        savings_total=savings_total,
        savings_unit=savings_unit,
        savings_pct=savings_pct,
        changed_ingredients=changed_count,
        changes=changes,
        optimized_ingredients=optimized_ingredients,
        optimized_recipe=RecipeOptimizationDraft(
            yield_qty=yield_qty,
            prep_time_minutes=draft_recipe.prep_time_minutes,
            baking_time_minutes=draft_recipe.baking_time_minutes,
            oven_temp_celsius=draft_recipe.oven_temp_celsius,
            rest_time_minutes=draft_recipe.rest_time_minutes,
            touch_minutes_standard=draft_recipe.touch_minutes_standard,
            oven_minutes_standard=draft_recipe.oven_minutes_standard,
            process_minutes=draft_recipe.process_minutes,
            waste_pct=draft_recipe.waste_pct,
            overhead_pct=draft_recipe.overhead_pct,
            trays_per_batch=draft_recipe.trays_per_batch,
            units_per_tray=draft_recipe.units_per_tray,
            instructions=str(ai_payload.get("instructions") or recipe.instructions or "").strip()
            or None,
            ingredients=draft_ingredients,
        ),
        ai_provider=(ai_response.metadata or {}).get("provider"),
        ai_model=str(ai_response.model or "").strip() or None,
    )
