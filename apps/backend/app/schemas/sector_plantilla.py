"""
Schemas para SectorPlantilla y su config_json validado con Pydantic
"""

from pydantic import BaseModel, Field, validator


class ModuleConfig(BaseModel):
    """Configuración de un módulo individual"""

    enabled: bool = True
    order: int = 0
    permissions: list[str] | None = None
    config: dict | None = None


class BrandingConfig(BaseModel):
    """Configuración de branding por sector"""

    color_primario: str = "#4f46e5"
    logo: str | None = None
    plantilla_inicio: str = "default"  # panaderia, taller, retail, etc.
    dashboard_template: str = "default"  # Plantilla HTML a usar


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

    class Config:
        json_schema_extra = {
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

    @validator("modules", pre=True)
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

    class Config:
        from_attributes = True


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
