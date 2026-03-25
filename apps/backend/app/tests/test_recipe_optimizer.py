from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.core.products import Product
from app.models.recipes import Recipe, RecipeIngredient
from app.services.ai.base import AIResponse, AITask
from app.services.ai.service import AIService
from app.services.recipe_optimizer import optimize_recipe_with_ai
from app.schemas.recipes import RecipeOptimizationRequest


def test_optimize_recipe_with_ai_respects_locked_ingredients(db, tenant_minimal, monkeypatch):
    tenant_id = tenant_minimal["tenant_id"]

    finished_product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="PAN-OPT",
        name="Pan optimizado",
        price=Decimal("2.50"),
        active=True,
        stock=0,
        unit="uds",
    )
    flour = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="HARINA-OPT",
        name="Harina panadera",
        active=True,
        stock=0,
        unit="kg",
        is_raw_material=True,
    )
    salt = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="SAL-OPT",
        name="Sal fina",
        active=True,
        stock=0,
        unit="kg",
        is_raw_material=True,
    )
    recipe = Recipe(
        id=uuid4(),
        tenant_id=tenant_id,
        product_id=finished_product.id,
        name="Receta pan base",
        yield_qty=10,
        total_cost=Decimal("10.50"),
        is_active=True,
    )
    flour_line = RecipeIngredient(
        id=uuid4(),
        recipe_id=recipe.id,
        product_id=flour.id,
        qty=Decimal("10.0000"),
        unit="kg",
        purchase_packaging="Saco 25 kg",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("25.0000"),
        line_order=0,
    )
    salt_line = RecipeIngredient(
        id=uuid4(),
        recipe_id=recipe.id,
        product_id=salt.id,
        qty=Decimal("0.5000"),
        unit="kg",
        purchase_packaging="Bolsa 10 kg",
        qty_per_package=Decimal("10.0000"),
        package_unit="kg",
        package_cost=Decimal("10.0000"),
        line_order=1,
    )

    db.add_all([finished_product, flour, salt, recipe, flour_line, salt_line])
    db.commit()

    async def fake_query(**kwargs):
        payload = {
            "summary": "Reducir harina sin tocar la sal bloqueada.",
            "assumptions": ["La harina admite un ajuste moderado."],
            "warnings": [],
            "yield_qty": 10,
            "waste_pct": 0,
            "overhead_pct": 0,
            "ingredients": [
                {
                    "product_id": str(flour.id),
                    "qty": 9.0,
                    "reason": "Se baja 10% para reducir coste del lote.",
                },
                {
                    "product_id": str(salt.id),
                    "qty": 0.45,
                    "reason": "La IA propuso bajar sal, pero debe quedar bloqueada.",
                },
            ],
        }
        return AIResponse(
            task=AITask.ANALYSIS,
            content=json.dumps(payload),
            model="test-model",
            metadata={"provider": "test-provider"},
        )

    monkeypatch.setattr(AIService, "query", staticmethod(fake_query))

    result = asyncio.run(
        optimize_recipe_with_ai(
            db=db,
            tenant_id=tenant_id,
            user_id="tester",
            recipe_id=recipe.id,
            request=RecipeOptimizationRequest(
                locked_product_ids=[salt.id],
                max_ingredients_to_change=2,
            ),
        )
    )

    optimized_by_id = {str(item.product_id): item for item in result.optimized_ingredients}

    assert optimized_by_id[str(flour.id)].qty == pytest.approx(9.0)
    assert optimized_by_id[str(flour.id)].changed is True
    assert optimized_by_id[str(salt.id)].qty == pytest.approx(0.5)
    assert optimized_by_id[str(salt.id)].locked is True
    assert result.savings_total > 0
    assert result.changed_ingredients == 1
    assert result.optimized.full_cost_unit < result.current.full_cost_unit


def test_optimize_recipe_with_ai_rejects_invalid_json(db, tenant_minimal, monkeypatch):
    tenant_id = tenant_minimal["tenant_id"]

    finished_product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="PAN-ERR",
        name="Pan error",
        active=True,
        stock=0,
        unit="uds",
    )
    flour = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="HARINA-ERR",
        name="Harina",
        active=True,
        stock=0,
        unit="kg",
        is_raw_material=True,
    )
    recipe = Recipe(
        id=uuid4(),
        tenant_id=tenant_id,
        product_id=finished_product.id,
        name="Receta invalida",
        yield_qty=5,
        total_cost=Decimal("5.00"),
        is_active=True,
    )
    ingredient = RecipeIngredient(
        id=uuid4(),
        recipe_id=recipe.id,
        product_id=flour.id,
        qty=Decimal("5.0000"),
        unit="kg",
        purchase_packaging="Saco",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("20.0000"),
        line_order=0,
    )
    db.add_all([finished_product, flour, recipe, ingredient])
    db.commit()

    async def fake_query(**kwargs):
        return AIResponse(
            task=AITask.ANALYSIS,
            content="respuesta sin json",
            model="test-model",
            metadata={"provider": "test-provider"},
        )

    monkeypatch.setattr(AIService, "query", staticmethod(fake_query))

    with pytest.raises(ValueError, match="JSON valido"):
        asyncio.run(
            optimize_recipe_with_ai(
                db=db,
                tenant_id=tenant_id,
                user_id="tester",
                recipe_id=recipe.id,
                request=RecipeOptimizationRequest(),
            )
        )


def test_optimize_recipe_with_ai_preserves_line_identity_for_duplicate_products(
    db, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]

    finished_product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="PAN-DUP",
        name="Pan con duplicados",
        active=True,
        stock=0,
        unit="uds",
    )
    flour = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="HARINA-DUP",
        name="Harina duplicada",
        active=True,
        stock=0,
        unit="kg",
        is_raw_material=True,
    )
    recipe = Recipe(
        id=uuid4(),
        tenant_id=tenant_id,
        product_id=finished_product.id,
        name="Receta con lineas repetidas",
        yield_qty=8,
        total_cost=Decimal("8.00"),
        is_active=True,
    )
    flour_line_a = RecipeIngredient(
        id=uuid4(),
        recipe_id=recipe.id,
        product_id=flour.id,
        qty=Decimal("3.0000"),
        unit="kg",
        purchase_packaging="Saco 25 kg",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("20.0000"),
        line_order=0,
    )
    flour_line_b = RecipeIngredient(
        id=uuid4(),
        recipe_id=recipe.id,
        product_id=flour.id,
        qty=Decimal("1.5000"),
        unit="kg",
        purchase_packaging="Saco 25 kg",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("20.0000"),
        line_order=1,
    )

    db.add_all([finished_product, flour, recipe, flour_line_a, flour_line_b])
    db.commit()

    async def fake_query(**kwargs):
        payload = {
            "summary": "Se ajusta harina sin perder trazabilidad por linea.",
            "assumptions": [],
            "warnings": [],
            "yield_qty": 8,
            "ingredients": [
                {
                    "product_id": str(flour.id),
                    "qty": 2.8,
                    "reason": "Ajuste conservador de harina.",
                }
            ],
        }
        return AIResponse(
            task=AITask.ANALYSIS,
            content=json.dumps(payload),
            model="test-model",
            metadata={"provider": "test-provider"},
        )

    monkeypatch.setattr(AIService, "query", staticmethod(fake_query))

    result = asyncio.run(
        optimize_recipe_with_ai(
            db=db,
            tenant_id=tenant_id,
            user_id="tester",
            recipe_id=recipe.id,
            request=RecipeOptimizationRequest(max_ingredients_to_change=2),
        )
    )

    assert len(result.changes) == 2
    assert [change.line_order for change in result.changes] == [0, 1]
    assert len({(str(change.product_id), change.line_order) for change in result.changes}) == 2
    assert any("ingredientes repetidos" in warning.lower() for warning in result.warnings)
