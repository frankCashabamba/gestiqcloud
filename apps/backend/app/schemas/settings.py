"""Schemas Pydantic para Configuración del Tenant"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# TENANT SETTINGS
# ============================================================================


class TenantSettingsResponse(BaseModel):
    """Schema de respuesta de configuración del tenant"""

    tenant_id: UUID

    # Configuración general
    nombre_empresa: str
    pais: str = Field(..., pattern="^(ES|EC)$", description="País del tenant")
    moneda_predeterminada: str = Field(default="EUR", pattern="^(EUR|USD)$")
    idioma: str = Field(default="es", pattern="^(es|en)$")

    # Módulos habilitados
    modulos_activos: list[str] = Field(
        default_factory=list,
        description="Lista de módulos activos: pos, inventory, sales, purchases, expenses, hr, finance",
    )

    # Configuración fiscal
    tipo_regimen_fiscal: str | None = Field(
        None, description="Régimen fiscal (ES: general, EC: RISE, etc)"
    )
    iva_incluido_precios: bool = Field(default=True, description="Si los precios incluyen IVA")
    tasa_iva_defecto: float = Field(
        default=0.21, ge=0, le=1, description="Tasa de IVA por defecto (0-1)"
    )

    # Configuración de facturación electrónica
    einvoicing_enabled: bool = Field(
        default=False, description="Si la e-facturación está habilitada"
    )
    einvoicing_provider: str | None = Field(None, pattern="^(sri|facturae|none)$")

    # Configuración de POS
    pos_enabled: bool = Field(default=False)
    pos_offline_mode: bool = Field(default=True)
    pos_print_width_mm: int = Field(default=58, pattern="^(58|80)$")

    # Configuración de inventario
    inventory_negative_stock: bool = Field(default=False, description="Permitir stock negativo")
    inventory_track_lots: bool = Field(default=False, description="Tracking de lotes/series")
    inventory_track_expiry: bool = Field(default=False, description="Tracking de caducidad")

    # Configuración de pagos
    payment_providers: list[str] = Field(
        default_factory=list, description="stripe, kushki, payphone"
    )

    # Metadata adicional (flexible)
    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MODULE SETTINGS UPDATE
# ============================================================================


class ModuleSettingsUpdate(BaseModel):
    """Schema para actualizar configuración de módulos específicos"""

    # General
    moneda_predeterminada: str | None = Field(None, pattern="^(EUR|USD)$")
    idioma: str | None = Field(None, pattern="^(es|en)$")

    # Fiscal
    tipo_regimen_fiscal: str | None = None
    iva_incluido_precios: bool | None = None
    tasa_iva_defecto: float | None = Field(None, ge=0, le=1)

    # E-invoicing
    einvoicing_enabled: bool | None = None
    einvoicing_provider: str | None = Field(None, pattern="^(sri|facturae|none)$")

    # POS
    pos_enabled: bool | None = None
    pos_offline_mode: bool | None = None
    pos_print_width_mm: int | None = Field(None, pattern="^(58|80)$")

    # Inventory
    inventory_negative_stock: bool | None = None
    inventory_track_lots: bool | None = None
    inventory_track_expiry: bool | None = None

    # Payments
    payment_providers: list[str] | None = None

    # Metadata
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# MODULE INFO (para listar módulos disponibles)
# ============================================================================


class ModuleInfo(BaseModel):
    """Información de un módulo del sistema"""

    code: str = Field(..., description="Código del módulo (ej: pos, sales, inventory)")
    name: str = Field(..., description="Nombre legible del módulo")
    description: str = Field(..., description="Descripción del módulo")
    category: str = Field(..., pattern="^(core|sales|purchases|finance|hr|config)$")
    available_countries: list[str] = Field(..., description="Países donde está disponible")
    requires_modules: list[str] = Field(default_factory=list, description="Módulos dependientes")
    enabled_by_default: bool = Field(default=False)
    icon: str | None = Field(None, description="Icono del módulo (nombre o emoji)")


class ModuleListResponse(BaseModel):
    """Lista de módulos disponibles"""

    modules: list[ModuleInfo]
    total: int


# ============================================================================
# TENANT ACTIVATION (onboarding)
# ============================================================================


class TenantActivationRequest(BaseModel):
    """Request para activar módulos en el tenant"""

    modulos_activar: list[str] = Field(
        ..., description="Códigos de módulos a activar", min_length=1
    )
    configuracion_inicial: ModuleSettingsUpdate | None = Field(
        None, description="Configuración inicial opcional"
    )


class TenantActivationResponse(BaseModel):
    """Respuesta de activación de tenant"""

    tenant_id: UUID
    modulos_activados: list[str]
    modulos_fallidos: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    configuracion: TenantSettingsResponse

    model_config = ConfigDict(from_attributes=True)
