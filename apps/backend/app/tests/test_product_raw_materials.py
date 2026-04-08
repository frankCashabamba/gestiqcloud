from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.core.products import Product
from app.models.recipes import RecipeIngredient
from app.models.tenant import Tenant
from app.modules.production.interface.http.tenant import RecipeCreate, create_recipe
from app.modules.products.interface.http.tenant import ProductCreate, create_product
from app.services.product_raw_materials import sync_product_as_raw_material_from_recipe_line


def _request_for_tenant(tenant_id: str):
    return SimpleNamespace(
        state=SimpleNamespace(tenant_id=tenant_id, access_claims={"tenant_id": tenant_id})
    )


def _claims_for_tenant(tenant_id: str) -> dict[str, str]:
    return {"tenant_id": str(tenant_id), "user_id": str(uuid4())}


def test_create_product_rejects_generic_unit_for_bakery_raw_material(db):
    tenant = Tenant(
        id=uuid4(), name="Panaderia Test", slug="pan-raw", sector_template_name="panaderia"
    )
    db.add(tenant)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        create_product(
            ProductCreate(
                name="Harina",
                price=0,
                stock=0,
                unit="unit",
                is_raw_material=True,
            ),
            request=_request_for_tenant(str(tenant.id)),
            db=db,
        )

    assert exc.value.status_code == 400
    assert "materias primas" in str(exc.value.detail).lower()


def test_sync_product_marks_product_as_raw_material_and_updates_unit_for_bakery(db):
    tenant = Tenant(
        id=uuid4(),
        name="Panaderia Ingredientes",
        slug="pan-ingredientes",
        sector_template_name="panaderia",
    )
    flour = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="HAR-001",
        name="Harina",
        active=True,
        stock=0,
        unit="unit",
        price=0,
    )
    bread = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="PAN-001",
        name="Pan",
        active=True,
        stock=0,
        unit="unit",
        price=1,
    )
    db.add_all([tenant, flour, bread])
    db.commit()

    changed = sync_product_as_raw_material_from_recipe_line(
        db,
        tenant_id=tenant.id,
        product=flour,
        unit="kg",
        package_unit="kg",
    )

    db.commit()
    db.refresh(flour)

    assert changed is True
    assert flour.is_raw_material is True
    assert flour.unit == "kg"


def test_create_recipe_uses_product_cost_when_package_cost_is_missing(db):
    tenant = Tenant(
        id=uuid4(),
        name="Panaderia Costeo",
        slug="pan-costeo",
        sector_template_name="panaderia",
    )
    ingredient = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="HAR-002",
        name="Harina Premium",
        active=True,
        stock=0,
        unit="kg",
        cost_price=10,
    )
    finished = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="PAN-002",
        name="Pan Premium",
        active=True,
        stock=0,
        unit="unit",
    )
    db.add_all([tenant, ingredient, finished])
    db.commit()

    recipe = create_recipe(
        RecipeCreate(
            name="Receta sin costo de paquete",
            product_id=finished.id,
            yield_qty=10,
            ingredients=[
                {
                    "product_id": ingredient.id,
                    "qty": 2,
                    "unit": "kg",
                    "purchase_packaging": "Saco 50 kg",
                    "qty_per_package": 50,
                    "package_unit": "kg",
                    "package_cost": 0,
                }
            ],
        ),
        db=db,
        claims=_claims_for_tenant(tenant.id),
    )

    db.refresh(recipe)
    assert float(recipe.total_cost or 0) == pytest.approx(20.0, rel=1e-6)

    stored_line = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe.id).one()
    assert float(stored_line.package_cost or 0) == pytest.approx(500.0, rel=1e-6)
