"""
Schemas para SectorPlantilla y su config_json validado con Pydantic
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModuleConfig(BaseModel):
    """Configuración de un módulo individual"""

    enabled: bool = True
    order: int = 0
    permissions: list[str] | None = None
    config: dict | None = None


class SectorUnit(BaseModel):
    """Unidad de medida para un sector"""

    code: str = Field(..., description="Código de la unidad (unit, kg, l, etc.)")
    label: str = Field(..., description="Etiqueta para mostrar (Unidad, Kilogramo, etc.)")


class FormatRule(BaseModel):
    """Regla de formateo para un sector"""

    decimals: int = 0
    suffix: str = ""
    metric: str | None = None


class BrandingConfig(BaseModel):
    """Configuración de branding y visualización por sector"""

    # Branding visual
    color_primario: str = "#4f46e5"
    logo: str | None = None
    plantilla_inicio: str = "default"  # panaderia, taller, retail, etc.
    dashboard_template: str = "default"  # Plantilla HTML a usar

    # NUEVO: Configuración visual del sector (elimina hardcoding)
    icon: str = "🏢"  # Emoji representativo del sector
    displayName: str = "General"  # Nombre legible del sector

    # NUEVO: Unidades de medida por sector
    units: list[SectorUnit] = Field(
        default_factory=lambda: [
            SectorUnit(code="unit", label="Unidad"),
            SectorUnit(code="kg", label="Kilogramo"),
            SectorUnit(code="l", label="Litro"),
        ],
        description="Unidades de medida disponibles para este sector",
    )

    # NUEVO: Reglas de formateo específicas del sector
    format_rules: dict[str, FormatRule] = Field(
        default_factory=dict, description="Reglas de formateo (quantity, weight, date, etc.)"
    )

    # NUEVO: Configuración de impresión
    print_config: dict = Field(
        default_factory=lambda: {
            "width": 58,
            "fontSize": 10,
            "showLogo": True,
            "showDetails": False,
        },
        description="Configuración de impresión por sector",
    )

    # NUEVO: Validaciones específicas del sector
    required_fields: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Campos requeridos por contexto (product, inventory, sale)",
    )


class DefaultsConfig(BaseModel):
    """Valores por defecto del sector"""

    categories: list[str] = Field(default_factory=list)
    tax_rate: float = 0.15
    currency: str = "EUR"
    locale: str = "es"
    timezone: str = "Europe/Madrid"
    price_includes_tax: bool = True


class POSConfig(BaseModel):
    """Configuración específica de POS por sector"""

    receipt_width_mm: int = 58
    print_mode: str = "system"
    return_window_days: int = 15
    enable_weights: bool = False
    enable_batch_tracking: bool = False


class InventoryConfig(BaseModel):
    """Configuración de inventario por sector"""

    enable_expiry_tracking: bool = False
    enable_lot_tracking: bool = False
    enable_serial_tracking: bool = False
    auto_reorder: bool = False
    reorder_point_days: int = 7


class SectorConfigJSON(BaseModel):
    """
    Schema completo del campo config_json de SectorPlantilla

    Este schema valida toda la configuración que se aplicará
    cuando se cree un tenant con este sector.
    """

    modules: dict[str, ModuleConfig] = Field(
        default_factory=dict,
        description="Configuración de módulos habilitados/deshabilitados",
    )
    branding: BrandingConfig = Field(
        default_factory=BrandingConfig,
        description="Configuración de marca y apariencia",
    )
    defaults: DefaultsConfig = Field(
        default_factory=DefaultsConfig, description="Valores por defecto del negocio"
    )
    pos: POSConfig = Field(default_factory=POSConfig, description="Configuración del módulo POS")
    inventory: InventoryConfig = Field(
        default_factory=InventoryConfig, description="Configuración de inventario"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "modules": {
                    "pos": {"enabled": True, "order": 5},
                    "ventas": {"enabled": True, "order": 10},
                    "inventario": {"enabled": True, "order": 20},
                    "facturacion": {"enabled": True, "order": 15},
                    "contabilidad": {"enabled": False},
                },
                "branding": {
                    "color_primario": "#8B4513",
                    "plantilla_inicio": "panaderia",
                    "dashboard_template": "panaderia_dashboard.html",
                    "icon": "🥐",
                    "displayName": "Panadería",
                    "units": [
                        {"code": "unit", "label": "Unidad"},
                        {"code": "kg", "label": "Kilogramo"},
                        {"code": "g", "label": "Gramo"},
                        {"code": "dozen", "label": "Docena"},
                    ],
                    "format_rules": {
                        "quantity": {"decimals": 0, "suffix": "uds"},
                        "weight": {"metric": "kg"},
                        "date": {"suffix": "dd/MMM"},
                    },
                    "print_config": {
                        "width": 58,
                        "fontSize": 9,
                        "showLogo": False,
                        "showDetails": False,
                    },
                    "required_fields": {"product": ["expires_at"], "inventory": ["expires_at"]},
                },
                "defaults": {
                    "categories": ["Pan", "Pasteles", "Bollería", "Bebidas"],
                    "tax_rate": 0.15,
                    "currency": "EUR",
                },
                "pos": {
                    "receipt_width_mm": 58,
                    "enable_weights": True,
                    "enable_batch_tracking": True,
                },
                "inventory": {
                    "enable_expiry_tracking": True,
                    "enable_lot_tracking": True,
                    "auto_reorder": True,
                    "reorder_point_days": 3,
                },
            }
        }
    )

    @field_validator("modules", mode="before")
    def validate_modules(cls, v):
        """Validar que los módulos sean válidos"""
        valid_modules = {
            "pos",
            "ventas",
            "facturacion",
            "inventario",
            "contabilidad",
            "compras",
            "clientes",
            "suppliers",
            "finanzas",
            "expenses",
            "importador",
            "hr",
            "settings",
            "users",
        }

        if isinstance(v, dict):
            invalid = set(v.keys()) - valid_modules
            if invalid:
                raise ValueError(f"Módulos no válidos: {invalid}")

        return v


class SectorPlantillaRead(BaseModel):
    """Schema para leer SectorPlantilla desde la API"""

    id: int
    name: str
    tipo_empresa_id: int
    tipo_negocio_id: int
    config_json: SectorConfigJSON

    model_config = ConfigDict(from_attributes=True)


class SectorPlantillaCreate(BaseModel):
    """Schema para crear nueva plantilla de sector"""

    name: str
    tipo_empresa_id: int
    tipo_negocio_id: int
    config_json: SectorConfigJSON


class ApplySectorTemplateRequest(BaseModel):
    """Request para aplicar plantilla a un tenant"""

    tenant_id: str
    sector_plantilla_id: int
    override_existing: bool = False


class SectorConfigUpdateRequest(BaseModel):
    """Request para actualizar configuración de sector (Admin UI - FASE 6)"""

    config: SectorConfigJSON = Field(..., description="Nueva configuración completa del sector")
    reason: str | None = Field(None, description="Razón del cambio (opcional, para auditoría)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "config": {
                "branding": {"icon": "🥐", "displayName": "Panadería", "color_primario": "#8B4513"},
                "defaults": {"tax_rate": 0.15, "currency": "EUR"},
                "modules": {"pos": {"enabled": True}},
                "pos": {"receipt_width_mm": 58},
                "inventory": {"enable_expiry_tracking": True}
            },
            "reason": "Actualizar color primario y cambiar configuración de inventario"
        }
    })


class SectorConfigResponse(BaseModel):
    """Response con configuración actual de un sector"""

    code: str
    name: str
    config: SectorConfigJSON
    last_modified: str | None = None
    modified_by: str | None = None
    config_version: int = 1

    model_config = ConfigDict(from_attributes=True)
