import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.modules.imports.infrastructure.country_packs import CountryPackRegistry, create_registry
from app.modules.imports.infrastructure.validators import (
    BankStatementValidator,
    ExpenseReceiptValidator,
    InvoiceValidator,
    ProductListValidator,
)


def setup_country_registry() -> CountryPackRegistry:
    registry = create_registry()
    return registry


def setup_country_validators(registry: CountryPackRegistry) -> dict:
    validators = {}

    for country_code in registry.list_all():
        pack = registry.get(country_code)

        validators[country_code] = {
            "invoice": InvoiceValidator(pack),
            "expense": ExpenseReceiptValidator(pack),
            "bank": BankStatementValidator(pack),
            "products": ProductListValidator(pack),
        }

    return validators


def configure_tenant_country(
    tenant_id: str, country_code: str, registry: CountryPackRegistry
) -> dict:
    pack = registry.get(country_code)

    if not pack:
        return {"error": f"Country pack {country_code} not found"}

    return {
        "tenant_id": tenant_id,
        "country_code": country_code,
        "currency": pack.get_currency(),
        "field_aliases": pack.get_field_aliases(),
        "configured": True,
    }


if __name__ == "__main__":
    print("Setting up Sprint 3 Country Packs...")

    registry = setup_country_registry()
    print(f"✓ Country registry initialized with {len(registry.list_all())} packs")
    print(f"  Countries: {', '.join(registry.list_all())}")

    validators = setup_country_validators(registry)
    print(f"✓ Country-specific validators created for {len(validators)} countries")

    ec_config = configure_tenant_country("test-tenant", "EC", registry)
    print(f"✓ Sample tenant configuration (EC): {ec_config}")

    es_config = configure_tenant_country("test-tenant", "ES", registry)
    print(f"✓ Sample tenant configuration (ES): {es_config}")

    print("✓ Sprint 3 setup complete")
    print("  - Country packs registered")
    print("  - Validators configured per country")
    print("  - Tenant configuration enabled")
