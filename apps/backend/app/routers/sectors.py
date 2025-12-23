"""
Router para Sectores (Plantillas de Negocio)

Endpoints:
- GET  /api/v1/sectors/{code}/units        # Obtener unidades de medida
- GET  /api/v1/sectors/{code}/config       # Obtener configuración completa
- GET  /api/v1/sectors/{code}/full-config  # Alias para /config
- GET  /api/v1/sectors/{code}/fields/{module}  # Campos por módulo
- GET  /api/v1/sectors/{code}/features     # Features habilitados
- GET  /api/v1/sectors/{code}/validations  # Reglas de validación dinámicas
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.company.company import SectorValidationRule
from app.services.sector_service import get_sector_or_404  # Centraliza query sector

router = APIRouter(prefix="/api/v1/sectors", tags=["Sectors"])


@router.get("/{code}/units", summary="Obtener unidades de medida del sector")
def get_sector_units(code: str, db: Session = Depends(get_db)):
    """
    Obtiene unidades de medida (units) configuradas para un sector.

    Carga desde: sector_templates.template_config.branding.units

    Args:
        code: Código del sector (ej: 'panaderia', 'taller')

    Returns:
        Lista de unidades con estructura:
        [
          { "code": "unit", "label": "Unidad" },
          { "code": "kg", "label": "Kilogramo" },
          { "code": "g", "label": "Gramo" },
          { "code": "dozen", "label": "Docena" }
        ]
    """
    try:
        sector = get_sector_or_404(code, db)

        # Extraer units del template_config
        template_config = sector.template_config or {}
        branding = template_config.get("branding", {})
        units = branding.get("units", [])

        # Fallback a unidades por defecto si no existen
        if not units:
            units = [
                {"code": "unit", "label": "Unidad"},
                {"code": "kg", "label": "Kilogramo"},
                {"code": "l", "label": "Litro"},
            ]

        return {"ok": True, "code": code, "units": units}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo unidades del sector: {str(e)}"
        ) from e


@router.get("/{code}/config", summary="Obtener configuración completa del sector")
def get_sector_config(code: str, db: Session = Depends(get_db)):
    """
    Obtiene la configuración completa de un sector desde la BD (FASE 1).

    Incluye:
    - branding: icon, displayName, color, etc.
    - units: Unidades de medida
    - format_rules: Reglas de formateo
    - print_config: Configuración de impresión
    - required_fields: Campos requeridos
    - features: Features habilitados (expiry_tracking, lot_tracking, etc.)
    - fields: Aliases, validations, placeholders
    - defaults: Categorías, impuestos, moneda, etc.
    - endpoints: URLs de endpoints configurables
    - templates: Templates permitidos

    Args:
        code: Código del sector

    Returns:
        Configuración completa del sector
    """
    try:
        sector = get_sector_or_404(code, db)

        # Retornar template_config completo (PLAN_ELIMINACION_HARDCODING_COMPLETO.md)
        template_config = sector.template_config or {}

        return {
            "ok": True,
            "code": code.lower(),
            "name": sector.name,
            "description": sector.description,
            "sector": template_config,  # Estructura completa según plan
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo configuración del sector: {str(e)}"
        ) from e


@router.get(
    "/{code}/full-config", summary="Obtener configuración COMPLETA del sector (alias para /config)"
)
def get_sector_full_config(code: str, db: Session = Depends(get_db)):
    """
    Alias para GET /{code}/config. Mantiene compatibilidad con PLAN_ELIMINACION_HARDCODING_COMPLETO.

    Esta es la ruta propuesta en Fase 1 del plan de eliminación de hardcoding.
    """
    return get_sector_config(code, db)


@router.get("/{code}/fields/{module}", summary="Obtener campos por módulo (FASE 1)")
def get_sector_field_config(code: str, module: str, db: Session = Depends(get_db)):
    """
    Obtiene aliases, validaciones y placeholders para un módulo específico.

    Extrae de: template_config.fields[module]

    Args:
        code: Código del sector (panaderia, taller, etc.)
        module: Módulo específico (products, customers, inventory, etc.)

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
            status_code=500, detail=f"Error obteniendo configuración de campos: {str(e)}"
        ) from e


@router.get("/{code}/features", summary="Obtener features del sector (FASE 1)")
def get_sector_features(code: str, db: Session = Depends(get_db)):
    """
    Obtiene features booleanos para condicionales en frontend.

    Reemplaza: `if (sector.is_panaderia) { ... }`
    Con: `if (config.features.expiry_tracking) { ... }`

    Extrae de: template_config.features

    Args:
        code: Código del sector

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
            status_code=500, detail=f"Error obteniendo features del sector: {str(e)}"
        ) from e


@router.get("/{code}/placeholders", summary="Obtener placeholders dinámicos (FASE 4)")
def get_sector_placeholders(code: str, module: str | None = None, db: Session = Depends(get_db)):
    """
    Obtiene placeholders dinámicos para campos de formulario.

    Reemplaza hardcoded placeholders como:
    - `placeholder="Ej: H-2025-028"` → `getFieldPlaceholder(config, 'lote')`
    - `placeholder="Ej: SN-123456789"` → `getFieldPlaceholder(config, 'numero_serie')`

    Extrae de: template_config.fields[module].placeholders (si module especificado)
    O template_config.fields[*].placeholders (si no especificado)

    Args:
        code: Código del sector (panaderia, taller, etc.)
        module: Módulo opcional (products, inventory, customers, etc.)
                Si no se proporciona, retorna placeholders de todos los módulos

    Returns:
        {
            "ok": true,
            "code": "panaderia",
            "module": "inventory" | null,
            "placeholders": {
                "lote": "Ej: H-2025-028",
                "numero_serie": "Ej: SN-ALT-123456789",
                "ubicacion": "Ej: Vitrina-A, Horno-2"
            } | { "inventory": {...}, "products": {...}, ... }
        }
    """
    try:
        sector = get_sector_or_404(code, db)

        template_config = sector.template_config or {}
        fields_config = template_config.get("fields", {})

        if module:
            # Retornar placeholders para módulo específico
            module_config = fields_config.get(module, {})
            placeholders = module_config.get("placeholders", {})

            return {
                "ok": True,
                "code": code.lower(),
                "module": module,
                "placeholders": placeholders,
            }
        else:
            # Retornar placeholders de todos los módulos
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
            status_code=500, detail=f"Error obteniendo placeholders del sector: {str(e)}"
        ) from e


@router.get("/{code}/validations", summary="Obtener reglas de validación dinámicas (FASE 4)")
def get_sector_validations(code: str, context: str | None = None, db: Session = Depends(get_db)):
    """
    Obtiene reglas de validación dinámicas para un sector.

    Reemplaza hardcoded validations en useSectorValidation.ts
    Con reglas cargadas desde BD (sector_validation_rules)

    Args:
        code: Código del sector (panaderia, taller, etc.)
        context: Contexto opcional ('product', 'inventory', 'sale', 'customer')
                 Si no se proporciona, retorna todas las reglas del sector

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
                    "message": "Fecha de caducidad es obligatoria",
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

        # Query validation rules para el sector
        query = db.query(SectorValidationRule).filter(
            SectorValidationRule.sector_template_id == sector.id,
            SectorValidationRule.enabled,
        )

        # Filtrar por context si se proporciona
        if context:
            query = query.filter(SectorValidationRule.context == context)

        # Ordenar por order y created_at
        rules = query.order_by(SectorValidationRule.order, SectorValidationRule.created_at).all()

        # Mapear a dict para respuesta
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
            status_code=500, detail=f"Error obteniendo validaciones del sector: {str(e)}"
        ) from e
