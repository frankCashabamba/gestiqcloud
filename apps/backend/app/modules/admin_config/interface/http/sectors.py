"""
Router for Sectors (Business Templates)

Endpoints:
- GET  /api/v1/sectors/{code}/units        # Get measurement units
- GET  /api/v1/sectors/{code}/config       # Get complete configuration
- GET  /api/v1/sectors/{code}/full-config  # Alias for /config
- GET  /api/v1/sectors/{code}/fields/{module}  # Fields by module
- GET  /api/v1/sectors/{code}/features     # Enabled features
- GET  /api/v1/sectors/{code}/validations  # Dynamic validation rules
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.company.company import SectorValidationRule
from app.services.sector_service import get_sector_or_404

router = APIRouter(prefix="/api/v1/sectors", tags=["Sectors"])


@router.get("/{code}/units", summary="Get sector measurement units")
def get_sector_units(code: str, db: Session = Depends(get_db)):
    """
    Gets measurement units configured for a sector.

    Loads from: sector_templates.template_config.branding.units

    Args:
        code: Sector code (e.g., 'panaderia', 'taller')

    Returns:
        List of units with structure:
        [
          { "code": "unit", "label": "Unit" },
          { "code": "kg", "label": "Kilogram" },
          { "code": "g", "label": "Gram" },
          { "code": "dozen", "label": "Dozen" }
        ]
    """
    try:
        sector = get_sector_or_404(code, db)

        template_config = sector.template_config or {}
        branding = template_config.get("branding", {})
        units = branding.get("units", [])

        if not units:
            units = [
                {"code": "unit", "label": "Unit"},
                {"code": "kg", "label": "Kilogram"},
                {"code": "l", "label": "Liter"},
            ]

        return {"ok": True, "code": code, "units": units}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sector units: {str(e)}") from e


@router.get("/{code}/config", summary="Get complete sector configuration")
def get_sector_config(code: str, db: Session = Depends(get_db)):
    """
    Gets the complete configuration of a sector from DB (PHASE 1).

    Includes:
    - branding: icon, displayName, color, etc.
    - units: Measurement units
    - format_rules: Formatting rules
    - print_config: Print configuration
    - required_fields: Required fields
    - features: Enabled features (expiry_tracking, lot_tracking, etc.)
    - fields: Aliases, validations, placeholders
    - defaults: Categories, taxes, currency, etc.
    - endpoints: Configurable endpoint URLs
    - templates: Allowed templates

    Args:
        code: Sector code

    Returns:
        Complete sector configuration
    """
    try:
        sector = get_sector_or_404(code, db)

        template_config = sector.template_config or {}

        return {
            "ok": True,
            "code": code.lower(),
            "name": sector.name,
            "description": sector.description,
            "sector": template_config,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting sector configuration: {str(e)}"
        ) from e


@router.get("/{code}/full-config", summary="Get COMPLETE sector configuration (alias for /config)")
def get_sector_full_config(code: str, db: Session = Depends(get_db)):
    """
    Alias for GET /{code}/config. Maintains compatibility with hardcoding elimination plan.

    This is the route proposed in Phase 1 of the hardcoding elimination plan.
    """
    return get_sector_config(code, db)


@router.get("/{code}/fields/{module}", summary="Get fields by module (PHASE 1)")
def get_sector_field_config(code: str, module: str, db: Session = Depends(get_db)):
    """
    Gets aliases, validations and placeholders for a specific module.

    Extracts from: template_config.fields[module]

    Args:
        code: Sector code (panaderia, taller, etc.)
        module: Specific module (products, customers, inventory, etc.)

    Returns:
        {
            "ok": true,
            "code": "panaderia",
            "module": "products",
            "config": {
                "aliases": {...},
                "validations": {...},
                "placeholders": {...}
            }
        }
    """
    try:
        sector = get_sector_or_404(code, db)

        template_config = sector.template_config or {}
        fields_config = template_config.get("fields", {})
        module_config = fields_config.get(module, {})

        return {
            "ok": True,
            "code": code.lower(),
            "module": module,
            "config": {
                "aliases": module_config.get("aliases", {}),
                "validations": module_config.get("validations", {}),
                "placeholders": module_config.get("placeholders", {}),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting field configuration: {str(e)}"
        ) from e


@router.get("/{code}/features", summary="Get sector features (PHASE 1)")
def get_sector_features(code: str, db: Session = Depends(get_db)):
    """
    Gets boolean features for frontend conditionals.

    Replaces: `if (sector.is_panaderia) { ... }`
    With: `if (config.features.expiry_tracking) { ... }`

    Extracts from: template_config.features

    Args:
        code: Sector code

    Returns:
        {
            "ok": true,
            "code": "panaderia",
            "features": {
                "expiry_tracking": true,
                "lot_tracking": true,
                "serial_tracking": false,
                ...
            }
        }
    """
    try:
        sector = get_sector_or_404(code, db)

        template_config = sector.template_config or {}
        features = template_config.get("features", {})

        return {
            "ok": True,
            "code": code.lower(),
            "features": features,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting sector features: {str(e)}"
        ) from e


@router.get("/{code}/placeholders", summary="Get dynamic placeholders (PHASE 4)")
def get_sector_placeholders(code: str, module: str | None = None, db: Session = Depends(get_db)):
    """
    Gets dynamic placeholders for form fields.

    Replaces hardcoded placeholders like:
    - `placeholder="E.g.: H-2025-028"` → `getFieldPlaceholder(config, 'lote')`
    - `placeholder="E.g.: SN-123456789"` → `getFieldPlaceholder(config, 'numero_serie')`

    Extracts from: template_config.fields[module].placeholders (if module specified)
    Or template_config.fields[*].placeholders (if not specified)

    Args:
        code: Sector code (panaderia, taller, etc.)
        module: Optional module (products, inventory, customers, etc.)
                If not provided, returns placeholders from all modules

    Returns:
        {
            "ok": true,
            "code": "panaderia",
            "module": "inventory" | null,
            "placeholders": {
                "lote": "E.g.: H-2025-028",
                "numero_serie": "E.g.: SN-ALT-123456789",
                "ubicacion": "E.g.: Vitrina-A, Horno-2"
            } | { "inventory": {...}, "products": {...}, ... }
        }
    """
    try:
        sector = get_sector_or_404(code, db)

        template_config = sector.template_config or {}
        fields_config = template_config.get("fields", {})

        if module:
            module_config = fields_config.get(module, {})
            placeholders = module_config.get("placeholders", {})

            return {
                "ok": True,
                "code": code.lower(),
                "module": module,
                "placeholders": placeholders,
            }
        else:
            all_placeholders = {}
            for mod, config in fields_config.items():
                module_placeholders = config.get("placeholders", {})
                if module_placeholders:
                    all_placeholders[mod] = module_placeholders

            return {
                "ok": True,
                "code": code.lower(),
                "module": None,
                "placeholders": all_placeholders,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting sector placeholders: {str(e)}"
        ) from e


@router.get("/{code}/validations", summary="Get dynamic validation rules (PHASE 4)")
def get_sector_validations(code: str, context: str | None = None, db: Session = Depends(get_db)):
    """
    Gets dynamic validation rules for a sector.

    Replaces hardcoded validations in useSectorValidation.ts
    With rules loaded from DB (sector_validation_rules)

    Args:
        code: Sector code (panaderia, taller, etc.)
        context: Optional context ('product', 'inventory', 'sale', 'customer')
                 If not provided, returns all rules for the sector

    Returns:
        {
            "ok": true,
            "code": "panaderia",
            "validations": [
                {
                    "id": "uuid",
                    "context": "product",
                    "field": "expires_at",
                    "rule_type": "required",
                    "message": "Expiry date is required",
                    "level": "error",
                    "condition": {...},
                    "enabled": true,
                    "order": 1
                }
            ]
        }
    """
    try:
        sector = get_sector_or_404(code, db)

        query = db.query(SectorValidationRule).filter(
            SectorValidationRule.sector_template_id == sector.id,
            SectorValidationRule.enabled,
        )

        if context:
            query = query.filter(SectorValidationRule.context == context)

        rules = query.order_by(SectorValidationRule.order, SectorValidationRule.created_at).all()

        validations = [
            {
                "id": str(rule.id),
                "context": rule.context,
                "field": rule.field,
                "rule_type": rule.rule_type,
                "message": rule.message,
                "level": rule.level,
                "condition": rule.condition,
                "enabled": rule.enabled,
                "order": rule.order,
            }
            for rule in rules
        ]

        return {
            "ok": True,
            "code": code.lower(),
            "context": context,
            "validations": validations,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting sector validations: {str(e)}"
        ) from e
