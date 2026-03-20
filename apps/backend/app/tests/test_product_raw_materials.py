from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.core.products import Product
from app.models.tenant import Tenant
from app.modules.products.interface.http.tenant import ProductCreate, create_product
from app.services.product_raw_materials import sync_product_as_raw_material_from_recipe_line


def _request_for_tenant(tenant_id: str):
    return SimpleNamespace(state=SimpleNamespace(tenant_id=tenant_id, access_claims={"tenant_id": tenant_id}))


def test_create_product_rejects_generic_unit_for_bakery_raw_material(db):
    tenant = Tenant(id=uuid4(), name="Panaderia Test", slug="pan-raw", sector_template_name="panaderia")
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
