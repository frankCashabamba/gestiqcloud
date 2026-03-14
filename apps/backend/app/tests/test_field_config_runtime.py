from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.company.company import SectorTemplate
from app.models.core.ui_field_config import SectorFieldDefault
from app.models.tenant import Tenant


def test_admin_sector_fields_for_clientes_are_seeded_into_db(client: TestClient, db):
    response = client.get("/api/v1/admin/field-config/sector?module=clientes&sector=retail")

    assert response.status_code == 200
    body = response.json()
    field_names = [item["field"] for item in body["items"]]
    assert "whatsapp" in field_names
    assert "descuento_pct" in field_names

    rows = (
        db.query(SectorFieldDefault)
        .filter(SectorFieldDefault.sector == "retail", SectorFieldDefault.module == "clientes")
        .all()
    )
    assert len(rows) == len(body["items"])
    assert all(row.options == [] for row in rows)


def test_company_field_config_uses_db_seed_for_tenant_sector(client: TestClient, db):
    tenant = Tenant(id=uuid4(), name="Retail Co", slug="retail-co", sector_template_name="retail")
    db.add(tenant)
    db.commit()

    response = client.get("/api/v1/company/settings/fields?module=clientes&empresa=retail-co")

    assert response.status_code == 200
    body = response.json()
    field_names = [item["field"] for item in body["items"]]
    assert "whatsapp" in field_names
    assert "moneda" in field_names
    assert "contacto_nombre" not in field_names


def test_admin_sector_fields_canonicalize_aliases(client: TestClient, db):
    response = client.get("/api/v1/admin/field-config/sector?module=clientes&sector=bazar")

    assert response.status_code == 200
    body = response.json()
    assert body["sector"] == "retail"
    field_names = [item["field"] for item in body["items"]]
    assert "whatsapp" in field_names


def test_admin_sector_fields_resolve_products_alias(client: TestClient, db):
    response = client.get("/api/v1/admin/field-config/sector?module=products&sector=retail")

    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "productos"
    assert body["requested_module"] == "products"
    field_names = [item["field"] for item in body["items"]]
    assert "marca" in field_names
    assert "stock_minimo" in field_names


def test_company_field_config_uses_products_alias_for_tenant_sector(client: TestClient, db):
    tenant = Tenant(
        id=uuid4(), name="Retail Products", slug="retail-products", sector_template_name="retail"
    )
    db.add(tenant)
    db.commit()

    response = client.get("/api/v1/company/settings/fields?module=products&empresa=retail-products")

    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "productos"
    assert body["requested_module"] == "products"
    field_names = [item["field"] for item in body["items"]]
    assert "marca" in field_names
    assert "color" in field_names


def test_company_field_config_reads_legacy_products_module_rows(client: TestClient, db):
    tenant = Tenant(
        id=uuid4(), name="Legacy Products", slug="legacy-products", sector_template_name="legacy"
    )
    db.add(tenant)
    db.add(
        SectorFieldDefault(
            sector="legacy",
            module="products",
            field="sku",
            visible=True,
            required=True,
            ord=10,
            label="SKU",
        )
    )
    db.commit()

    response = client.get("/api/v1/company/settings/fields?module=products&empresa=legacy-products")

    assert response.status_code == 200
    body = response.json()
    field_names = [item["field"] for item in body["items"]]
    assert "sku" in field_names


def test_admin_sector_fields_seed_suppliers_from_template_config(client: TestClient, db):
    sector = SectorTemplate(
        id=uuid4(),
        code="farmacia",
        name="Farmacia",
        template_config={
            "fields": {
                "suppliers": {
                    "items": [
                        {"field": "name", "required": True, "ord": 10, "label": "Nombre"},
                        {"field": "phone", "required": False, "ord": 20, "label": "Telefono"},
                    ]
                }
            }
        },
        is_active=True,
    )
    db.add(sector)
    db.commit()

    response = client.get("/api/v1/admin/field-config/sector?module=suppliers&sector=farmacia")

    assert response.status_code == 200
    body = response.json()
    field_names = [item["field"] for item in body["items"]]
    assert "name" in field_names
    assert "phone" in field_names

    rows = (
        db.query(SectorFieldDefault)
        .filter(SectorFieldDefault.sector == "farmacia", SectorFieldDefault.module == "suppliers")
        .order_by(SectorFieldDefault.ord.asc().nulls_last())
        .all()
    )
    assert [row.field for row in rows] == ["name", "phone"]
