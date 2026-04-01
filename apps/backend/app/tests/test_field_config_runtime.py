from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt_provider import get_token_service
from app.models.company.company import SectorTemplate
from app.models.core.ui_field_config import SectorFieldDefault
from app.models.tenant import Tenant


def _tenant_headers(tenant: Tenant, slug: str) -> dict[str, str]:
    token = get_token_service().issue_access(
        {
            "user_id": str(uuid4()),
            "tenant_id": str(tenant.id),
            "empresa_slug": slug,
            "scope": "tenant",
            "kind": "tenant",
            "sub": "tenant@example.com",
        }
    )
    return {"Authorization": f"Bearer {token}"}


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

    response = client.get(
        "/api/v1/company/settings/fields?module=clientes&empresa=retail-co",
        headers=_tenant_headers(tenant, "retail-co"),
    )

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

    response = client.get(
        "/api/v1/company/settings/fields?module=products&empresa=retail-products",
        headers=_tenant_headers(tenant, "retail-products"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["module"] == "productos"
    assert body["requested_module"] == "products"
    field_names = [item["field"] for item in body["items"]]
    assert "marca" in field_names
    assert "color" in field_names


def test_company_field_config_includes_raw_material_for_bakery_products(client: TestClient, db):
    tenant = Tenant(
        id=uuid4(), name="Bakery Products", slug="bakery-products", sector_template_name="panaderia"
    )
    db.add(tenant)
    db.commit()

    response = client.get(
        "/api/v1/company/settings/fields?module=products&empresa=bakery-products",
        headers=_tenant_headers(tenant, "bakery-products"),
    )

    assert response.status_code == 200
    body = response.json()
    field_names = [item["field"] for item in body["items"]]
    assert "is_raw_material" in field_names


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

    response = client.get(
        "/api/v1/company/settings/fields?module=products&empresa=legacy-products",
        headers=_tenant_headers(tenant, "legacy-products"),
    )

    assert response.status_code == 200
    body = response.json()
    field_names = [item["field"] for item in body["items"]]
    assert "sku" in field_names


def test_company_field_config_prioritizes_authenticated_tenant_over_empresa_query(
    client: TestClient, db
):
    retail_slug = f"retail-{uuid4().hex[:8]}"
    bakery_slug = f"bakery-{uuid4().hex[:8]}"
    retail = Tenant(id=uuid4(), name="Retail Co", slug=retail_slug, sector_template_name="retail")
    bakery = Tenant(
        id=uuid4(),
        name="Panaderia Co",
        slug=bakery_slug,
        sector_template_name="panaderia",
    )
    db.add_all([retail, bakery])
    db.commit()

    response = client.get(
        f"/api/v1/company/settings/fields?module=clientes&empresa={retail_slug}",
        headers=_tenant_headers(bakery, bakery_slug),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "tenant_slug_mismatch"


def test_company_field_config_requires_auth_for_company_lookup(client: TestClient, db):
    tenant = Tenant(id=uuid4(), name="Retail Co", slug="retail-co", sector_template_name="retail")
    db.add(tenant)
    db.commit()

    response = client.get("/api/v1/company/settings/fields?module=clientes&empresa=retail-co")

    assert response.status_code == 401
    assert response.json()["detail"] == "tenant_auth_required"


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


def test_company_field_config_rejects_non_ui_module_namespaces(client: TestClient):
    response = client.get("/api/v1/company/settings/fields?module=importador.file_support")

    assert response.status_code == 400
    assert response.json()["detail"] == "field_config_ui_only"


def test_admin_sector_fields_reject_reserved_non_ui_scope(client: TestClient):
    response = client.get(
        "/api/v1/admin/field-config/sector?module=importador.file_support&sector=_system"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "field_config_ui_only"


def test_admin_import_table_rejects_reserved_system_sector(client: TestClient):
    response = client.post(
        "/api/v1/admin/field-config/import-table",
        json={"table": "products", "module": "imports_products", "sector": "_system"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "field_config_ui_only"
