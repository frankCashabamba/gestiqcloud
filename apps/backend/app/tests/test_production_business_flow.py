from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


def _claims(tenant_id: str, user_id: str) -> dict[str, str]:
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
    }


def _request_for_tenant(tenant_id: str, user_id: str):
    return SimpleNamespace(state=SimpleNamespace(access_claims=_claims(tenant_id, user_id)))


def test_complete_production_requires_authenticated_user(db, tenant_minimal):
    from app.modules.production.interface.http.tenant import complete_production
    from app.schemas.production import ProductionOrderCompleteRequest

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            complete_production(
                uuid4(),
                ProductionOrderCompleteRequest(qty_produced=Decimal("1")),
                db=db,
                claims={"tenant_id": tenant_minimal["tenant_id_str"]},
            )
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "production_completion_requires_user"


def test_complete_production_consumes_inputs_and_generates_output(
    db, tenant_minimal, superuser_factory
):
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("Postgres-specific production flow test")

    from app.models.core.products import Product
    from app.models.inventory.stock import StockItem, StockMove
    from app.models.inventory.warehouse import Warehouse
    from app.models.recipes import Recipe, RecipeIngredient
    from app.modules.production.interface.http.tenant import (
        complete_production,
        create_production_order,
    )
    from app.schemas.production import ProductionOrderCompleteRequest, ProductionOrderCreate

    tenant_id = tenant_minimal["tenant_id"]
    tenant_id_str = tenant_minimal["tenant_id_str"]
    user = superuser_factory(username=f"prod_flow_{uuid4().hex[:8]}", tenant_id=tenant_id)

    warehouse = Warehouse(
        id=uuid4(),
        tenant_id=tenant_id,
        code="MAIN",
        name="Main production warehouse",
        is_active=True,
    )

    flour = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="HARINA-001",
        name="Harina panadera",
        active=True,
        stock=30,
        unit="kg",
    )
    yeast = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="LEV-001",
        name="Levadura",
        active=True,
        stock=12,
        unit="kg",
    )
    bread = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="PAN-001",
        name="Pan del dia",
        active=True,
        stock=0,
        unit="unit",
    )

    recipe = Recipe(
        id=uuid4(),
        tenant_id=tenant_id,
        product_id=bread.id,
        name="Receta base pan",
        yield_qty=10,
        total_cost=Decimal("18.00"),
        is_active=True,
    )
    flour_line = RecipeIngredient(
        recipe_id=recipe.id,
        product_id=flour.id,
        qty=Decimal("5.0000"),
        unit="kg",
        purchase_packaging="Saco 25 kg",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("25.0000"),
        line_order=0,
    )
    yeast_line = RecipeIngredient(
        recipe_id=recipe.id,
        product_id=yeast.id,
        qty=Decimal("1.0000"),
        unit="kg",
        purchase_packaging="Bolsa 10 kg",
        qty_per_package=Decimal("10.0000"),
        package_unit="kg",
        package_cost=Decimal("18.0000"),
        line_order=1,
    )

    stock_flour = StockItem(
        tenant_id=tenant_id,
        warehouse_id=warehouse.id,
        product_id=flour.id,
        qty=30,
    )
    stock_yeast = StockItem(
        tenant_id=tenant_id,
        warehouse_id=warehouse.id,
        product_id=yeast.id,
        qty=12,
    )
    stock_bread = StockItem(
        tenant_id=tenant_id,
        warehouse_id=warehouse.id,
        product_id=bread.id,
        qty=0,
    )

    db.add_all([warehouse, flour, yeast, bread])
    db.commit()

    db.add(recipe)
    db.commit()

    db.add_all([flour_line, yeast_line, stock_flour, stock_yeast, stock_bread])
    db.commit()

    claims = _claims(tenant_id_str, str(user.id))

    created = asyncio.run(
        create_production_order(
            ProductionOrderCreate(
                recipe_id=recipe.id,
                product_id=bread.id,
                warehouse_id=warehouse.id,
                qty_planned=Decimal("20"),
                scheduled_date=datetime.utcnow(),
                notes="batch for morning shift",
            ),
            db=db,
            claims=claims,
        )
    )

    assert created.status == "DRAFT"
    assert len(created.lines) == 2
    assert {str(line.ingredient_product_id) for line in created.lines} == {
        str(flour.id),
        str(yeast.id),
    }

    completed = asyncio.run(
        complete_production(
            created.id,
            ProductionOrderCompleteRequest(
                qty_produced=Decimal("18"),
                waste_qty=Decimal("2"),
                waste_reason="control sample",
                batch_number="LOT-TEST-001",
                notes="completed from automated test",
            ),
            db=db,
            claims=claims,
        )
    )

    assert completed.status == "COMPLETED"
    assert completed.qty_produced == Decimal("18")
    assert completed.waste_qty == Decimal("2")
    assert completed.batch_number == "LOT-TEST-001"
    assert all(line.qty_consumed == line.qty_required for line in completed.lines)

    flour_stock = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tenant_id_str,
            StockItem.warehouse_id == str(warehouse.id),
            StockItem.product_id == str(flour.id),
        )
        .one()
    )
    yeast_stock = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tenant_id_str,
            StockItem.warehouse_id == str(warehouse.id),
            StockItem.product_id == str(yeast.id),
        )
        .one()
    )
    bread_stock = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tenant_id_str,
            StockItem.warehouse_id == str(warehouse.id),
            StockItem.product_id == str(bread.id),
        )
        .one()
    )

    assert float(flour_stock.qty or 0) == 20.0
    assert float(yeast_stock.qty or 0) == 10.0
    assert float(bread_stock.qty or 0) == 18.0
    assert bread_stock.lot == "LOT-TEST-001"

    consume_moves = (
        db.query(StockMove)
        .filter(
            StockMove.tenant_id == tenant_id_str,
            StockMove.ref_type == "production_order",
            StockMove.ref_id == str(created.id),
            StockMove.kind == "production_consume",
        )
        .all()
    )
    output_move = (
        db.query(StockMove)
        .filter(
            StockMove.tenant_id == tenant_id_str,
            StockMove.ref_type == "production_order",
            StockMove.ref_id == str(created.id),
            StockMove.kind == "production_output",
        )
        .one()
    )

    assert len(consume_moves) == 2
    assert sorted(round(abs(float(move.qty or 0)), 3) for move in consume_moves) == [2.0, 10.0]
    assert float(output_move.qty or 0) == 18.0

    db.refresh(flour)
    db.refresh(yeast)
    db.refresh(bread)
    assert float(flour.stock or 0) == 20.0
    assert float(yeast.stock or 0) == 10.0
    assert float(bread.stock or 0) == 18.0


def test_list_production_orders_filters_by_scheduled_date(db, tenant_minimal, superuser_factory):
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("Postgres-specific production flow test")

    from app.models.core.products import Product
    from app.models.inventory.warehouse import Warehouse
    from app.models.recipes import Recipe, RecipeIngredient
    from app.modules.production.interface.http.tenant import (
        create_production_order,
        list_production_orders,
    )
    from app.schemas.production import ProductionOrderCreate

    tenant_id = tenant_minimal["tenant_id"]
    tenant_id_str = tenant_minimal["tenant_id_str"]
    user = superuser_factory(username=f"prod_sched_{uuid4().hex[:8]}", tenant_id=tenant_id)

    warehouse = Warehouse(
        id=uuid4(),
        tenant_id=tenant_id,
        code="PLAN",
        name="Planning warehouse",
        is_active=True,
    )
    ingredient = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="ING-001",
        name="Ingrediente base",
        active=True,
        stock=100,
        unit="kg",
    )
    finished = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="FIN-001",
        name="Producto final",
        active=True,
        stock=0,
        unit="unit",
    )
    recipe = Recipe(
        id=uuid4(),
        tenant_id=tenant_id,
        product_id=finished.id,
        name="Receta planificación",
        yield_qty=10,
        total_cost=Decimal("12.00"),
        is_active=True,
    )
    recipe_line = RecipeIngredient(
        recipe_id=recipe.id,
        product_id=ingredient.id,
        qty=Decimal("2.0000"),
        unit="kg",
        purchase_packaging="Saco",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("20.0000"),
        line_order=0,
    )

    db.add_all([warehouse, ingredient, finished])
    db.commit()

    db.add(recipe)
    db.commit()

    db.add(recipe_line)
    db.commit()

    claims = _claims(tenant_id_str, str(user.id))
    base_day = datetime(2026, 3, 12, 5, 0, 0)

    asyncio.run(
        create_production_order(
            ProductionOrderCreate(
                recipe_id=recipe.id,
                product_id=finished.id,
                warehouse_id=warehouse.id,
                qty_planned=Decimal("20"),
                scheduled_date=base_day,
                notes="turno madrugada",
            ),
            db=db,
            claims=claims,
        )
    )
    asyncio.run(
        create_production_order(
            ProductionOrderCreate(
                recipe_id=recipe.id,
                product_id=finished.id,
                warehouse_id=warehouse.id,
                qty_planned=Decimal("15"),
                scheduled_date=base_day + timedelta(days=1),
                notes="turno manana",
            ),
            db=db,
            claims=claims,
        )
    )

    result = asyncio.run(
        list_production_orders(
            scheduled_from="2026-03-12T00:00:00",
            scheduled_to="2026-03-12T23:59:59",
            db=db,
            claims=claims,
        )
    )

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].notes == "turno madrugada"


def test_planning_suggestions_use_recent_sales_stock_and_existing_plan(
    db, tenant_minimal, superuser_factory
):
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("Postgres-specific production flow test")

    from app.models.core.products import Product
    from app.models.inventory.stock import StockItem
    from app.models.inventory.warehouse import Warehouse
    from app.models.pos.receipt import POSReceipt, POSReceiptLine
    from app.models.pos.register import POSRegister, POSShift
    from app.models.recipes import Recipe, RecipeIngredient
    from app.modules.production.interface.http.tenant import (
        create_production_order,
        list_production_planning_suggestions,
    )
    from app.schemas.production import ProductionOrderCreate

    tenant_id = tenant_minimal["tenant_id"]
    tenant_id_str = tenant_minimal["tenant_id_str"]
    user = superuser_factory(username=f"prod_suggest_{uuid4().hex[:8]}", tenant_id=tenant_id)

    warehouse = Warehouse(
        id=uuid4(),
        tenant_id=tenant_id,
        code="BAKE",
        name="Bakehouse",
        is_active=True,
    )
    register = POSRegister(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Mostrador",
        active=True,
    )
    shift = POSShift(
        id=uuid4(),
        register_id=register.id,
        opened_by=user.id,
        opened_at=datetime(2026, 3, 8, 6, 0, 0),
        opening_float=Decimal("50.00"),
        status="open",
    )

    flour = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="HAR-002",
        name="Harina fuerza",
        active=True,
        stock=100,
        unit="kg",
    )
    bread = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        sku="PAN-002",
        name="Barra rustica",
        active=True,
        stock=1,
        unit="unit",
    )
    recipe = Recipe(
        id=uuid4(),
        tenant_id=tenant_id,
        product_id=bread.id,
        name="Barra rustica 500g",
        yield_qty=10,
        total_cost=Decimal("10.00"),
        is_active=True,
    )
    recipe_line = RecipeIngredient(
        recipe_id=recipe.id,
        product_id=flour.id,
        qty=Decimal("3.0000"),
        unit="kg",
        purchase_packaging="Saco 25 kg",
        qty_per_package=Decimal("25.0000"),
        package_unit="kg",
        package_cost=Decimal("22.0000"),
        line_order=0,
    )
    stock_bread = StockItem(
        tenant_id=tenant_id,
        warehouse_id=warehouse.id,
        product_id=bread.id,
        qty=1,
    )

    db.add_all([warehouse, register, flour, bread])
    db.commit()

    db.add(shift)
    db.commit()

    db.add(recipe)
    db.commit()

    db.add_all([recipe_line, stock_bread])
    db.commit()

    receipt_days = [
        datetime(2026, 3, 8, 8, 0, 0),
        datetime(2026, 3, 9, 8, 0, 0),
        datetime(2026, 3, 10, 8, 0, 0),
        datetime(2026, 3, 11, 8, 0, 0),
    ]
    sold_quantities = [3, 4, 4, 3]
    for index, (created_at, qty) in enumerate(
        zip(receipt_days, sold_quantities, strict=False), start=1
    ):
        receipt = POSReceipt(
            id=uuid4(),
            tenant_id=tenant_id,
            register_id=register.id,
            shift_id=shift.id,
            cashier_id=None,
            number=f"T-{index:03d}",
            status="paid",
            warehouse_id=warehouse.id,
            gross_total=Decimal("12.00"),
            tax_total=Decimal("1.20"),
            currency="USD",
            paid_at=created_at,
            created_at=created_at,
        )
        line = POSReceiptLine(
            id=uuid4(),
            receipt_id=receipt.id,
            product_id=bread.id,
            qty=Decimal(str(qty)),
            uom="unit",
            unit_price=Decimal("1.20"),
            tax_rate=Decimal("0.10"),
            discount_pct=Decimal("0.00"),
            line_total=Decimal(str(qty * 1.2)),
            net_total=Decimal(str(qty)),
            cogs_unit=Decimal("0.40"),
            cogs_total=Decimal(str(qty * 0.4)),
            gross_profit=Decimal(str(qty * 0.8)),
            gross_margin_pct=Decimal("0.6667"),
        )
        db.add_all([receipt, line])
    db.commit()

    claims = _claims(tenant_id_str, str(user.id))
    target_day = datetime(2026, 3, 12, 5, 0, 0)
    asyncio.run(
        create_production_order(
            ProductionOrderCreate(
                recipe_id=recipe.id,
                product_id=bread.id,
                warehouse_id=warehouse.id,
                qty_planned=Decimal("1"),
                scheduled_date=target_day,
                notes="reposicion ya planificada",
            ),
            db=db,
            claims=claims,
        )
    )

    suggestions = asyncio.run(
        list_production_planning_suggestions(
            target_date=target_day.date(),
            history_days=4,
            limit=5,
            db=db,
            claims=claims,
        )
    )

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.recipe_id == recipe.id
    assert suggestion.product_id == bread.id
    assert suggestion.avg_daily_sales == Decimal("3.500")
    assert suggestion.stock_on_hand == Decimal("1.000")
    assert suggestion.already_planned_qty == Decimal("1.000")
    assert suggestion.suggested_qty == Decimal("2")
