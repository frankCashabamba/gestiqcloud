from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4


def _claims(tenant_id: str, user_id: str) -> dict[str, str]:
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
    }


def _request_for_tenant(tenant_id: str, user_id: str):
    return SimpleNamespace(
        state=SimpleNamespace(access_claims=_claims(tenant_id, user_id))
    )


def test_complete_production_consumes_inputs_and_generates_output(
    db, tenant_minimal, superuser_factory
):
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

    db.add_all(
        [
            warehouse,
            flour,
            yeast,
            bread,
            recipe,
            flour_line,
            yeast_line,
            stock_flour,
            stock_yeast,
            stock_bread,
        ]
    )
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
