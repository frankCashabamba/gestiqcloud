from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.company.company import SectorTemplate
from app.models.core.global_catalogs import UnitOfMeasure
from app.services.unit_catalog_service import normalize_operational_unit
from app.utils.unit_converter import are_compatible_units, convert


def test_sector_units_fallback_uses_global_catalog(client: TestClient, db):
    sector = SectorTemplate(
        id=uuid4(),
        code="unit-fallback",
        name="Unit Fallback",
        template_config={"branding": {}},
        is_active=True,
    )
    db.add(sector)

    if not db.query(UnitOfMeasure).filter(UnitOfMeasure.code == "UN").first():
        db.add(UnitOfMeasure(code="UN", name="Unidad", abbreviation="un", active=True))
    if not db.query(UnitOfMeasure).filter(UnitOfMeasure.code == "KG").first():
        db.add(UnitOfMeasure(code="KG", name="Kilogramo", abbreviation="kg", active=True))
    db.commit()

    response = client.get("/api/v1/sectors/unit-fallback/units")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert {"code": "uds", "label": "Unidad"} in body["units"]
    assert {"code": "kg", "label": "Kilogramo"} in body["units"]


def test_tenant_units_catalog_publishes_normalized_runtime_codes(client: TestClient, db):
    if not db.query(UnitOfMeasure).filter(UnitOfMeasure.code == "UN").first():
        db.add(UnitOfMeasure(code="UN", name="Unidad", abbreviation="un", active=True))
    if not db.query(UnitOfMeasure).filter(UnitOfMeasure.code == "KG").first():
        db.add(UnitOfMeasure(code="KG", name="Kilogramo", abbreviation="kg", active=True))
    db.commit()

    response = client.get("/api/v1/tenant/catalogs/units")

    assert response.status_code == 200
    body = response.json()
    assert any(
        item["code"] == "uds"
        and item["catalog_code"] == "UN"
        and item["label"] == "Unidad"
        and item["name"] == "Unidad"
        and item["abbreviation"] == "un"
        for item in body
    )
    assert any(
        item["code"] == "kg"
        and item["catalog_code"] == "KG"
        and item["label"] == "Kilogramo"
        and item["name"] == "Kilogramo"
        and item["abbreviation"] == "kg"
        for item in body
    )


def test_normalize_operational_unit_canonicalizes_common_aliases():
    assert normalize_operational_unit("UN") == "uds"
    assert normalize_operational_unit("units") == "uds"
    assert normalize_operational_unit("lt") == "L"
    assert normalize_operational_unit("Cubeta 20L") == "cubeta_20l"


def test_unit_converter_treats_unit_and_uds_as_count_equivalents():
    assert are_compatible_units("unit", "uds") is True
    assert convert(3, "unit", "uds") == 3
