from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.modules.imports.infrastructure.country_packs import create_registry

router = APIRouter(prefix="/country-rules", tags=["country-rules"])

country_registry = create_registry()


@router.get("/available")
async def list_available_countries():
    return {
        "countries": country_registry.list_all(),
    }


@router.get("/{country_code}")
async def get_country_rules(country_code: str):
    pack = country_registry.get(country_code)

    if not pack:
        raise HTTPException(status_code=404, detail="Country pack not found")

    return {
        "country_code": pack.get_country_code(),
        "currency": pack.get_currency(),
        "field_aliases": pack.get_field_aliases(),
    }


@router.post("/{country_code}/validate-tax-id")
async def validate_tax_id(country_code: str, tax_id: str):
    pack = country_registry.get(country_code)

    if not pack:
        raise HTTPException(status_code=404, detail="Country pack not found")

    valid, error = pack.validate_tax_id(tax_id)

    return {
        "valid": valid,
        "error": error,
    }


@router.post("/{country_code}/validate-date")
async def validate_date_format(country_code: str, date_str: str):
    pack = country_registry.get(country_code)

    if not pack:
        raise HTTPException(status_code=404, detail="Country pack not found")

    valid, error = pack.validate_date_format(date_str)

    return {
        "valid": valid,
        "error": error,
    }


@router.post("/{country_code}/validate-fiscal")
async def validate_fiscal_fields(country_code: str, data: dict):
    pack = country_registry.get(country_code)

    if not pack:
        raise HTTPException(status_code=404, detail="Country pack not found")

    errors = pack.validate_fiscal_fields(data)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


@router.post("/{tenant_id}/configure/{country_code}")
async def configure_country_for_tenant(tenant_id: UUID, country_code: str):
    pack = country_registry.get(country_code)

    if not pack:
        raise HTTPException(status_code=404, detail="Country pack not found")

    return {
        "tenant_id": str(tenant_id),
        "country_code": country_code,
        "configured": True,
        "currency": pack.get_currency(),
    }
