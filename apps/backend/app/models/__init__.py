# Auto-generado: registra todos los modelos importándolos

# Core models
# Sistema IA + Incidencias + Alertas
from app.models.ai import Incident, NotificationChannel, NotificationLog, StockAlert
from app.models.auth.refresh_family import RefreshFamily

# Auth & Security
from app.models.auth.useradmis import SuperUser
from app.models.core.auditoria_importacion import AuditoriaImportacion
from app.models.core.clients import Cliente
from app.models.core.facturacion import (
    BankAccount,
    BankTransaction,
    InternalTransfer,
    Invoice,
    InvoiceTemp,
    MovimientoEstado,
    MovimientoTipo,
    Payment,
)
from app.models.core.invoiceLine import LineaFactura, LineaPanaderia, LineaTaller
from app.models.core.modulo import EmpresaModulo, Modulo, ModuloAsignado
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.core.settings import TenantSettings
from app.models.empresa.empresa import (
    CategoriaEmpresa,
    DiaSemana,
    HorarioAtencion,
    Idioma,
    Moneda,
    Pais,
    PerfilUsuario,
    PermisoAccionGlobal,
    RefLocale,
    RefTimezone,
    RolBase,
    SectorPlantilla,
    TipoEmpresa,
    TipoNegocio,
)

# Empresa (legacy)
from app.models.empresa.rolempresas import RolEmpresa
from app.models.empresa.settings import ConfiguracionEmpresa, ConfiguracionInventarioEmpresa
from app.models.empresa.usuario_rolempresa import UsuarioRolempresa
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.models.expenses import Gasto
from app.models.finance import BancoMovimiento, CajaMovimiento, CierreCaja
from app.models.hr import Empleado, Vacacion

# Imports system
from app.models.imports import ImportColumnMapping
from app.models.pos import (
    DocSeries,
    POSPayment,
    POSReceipt,
    POSReceiptLine,
    POSRegister,
    POSShift,
    StoreCredit,
    StoreCreditEvent,
)
from app.models.purchases import Compra, CompraLinea
from app.models.recipes import Recipe, RecipeIngredient

# Nuevos módulos profesionales
from app.models.sales import Venta
from app.models.security.auth_audit import AuthAudit
from app.models.suppliers import Proveedor, ProveedorContacto, ProveedorDireccion
from app.models.tenant import Tenant

__all__ = [
    # Core Facturación
    "BankAccount",
    "BankTransaction",
    "InternalTransfer",
    "Invoice",
    "InvoiceTemp",
    "MovimientoEstado",
    "MovimientoTipo",
    "Payment",
    # Core Invoice Lines
    "LineaFactura",
    "LineaPanaderia",
    "LineaTaller",
    # Core Models
    "EmpresaModulo",
    "Modulo",
    "ModuloAsignado",
    "Product",
    "Recipe",
    "RecipeIngredient",
    "ProductCategory",
    "AuditoriaImportacion",
    "Cliente",
    "TenantSettings",
    # Empresa
    "RolEmpresa",
    "ConfiguracionEmpresa",
    "ConfiguracionInventarioEmpresa",
    "UsuarioRolempresa",
    "UsuarioEmpresa",
    "CategoriaEmpresa",
    "DiaSemana",
    "HorarioAtencion",
    "Idioma",
    "Moneda",
    "Pais",
    "RefTimezone",
    "RefLocale",
    "PerfilUsuario",
    "PermisoAccionGlobal",
    "RolBase",
    "SectorPlantilla",
    "TipoEmpresa",
    "TipoNegocio",
    # Auth & Security
    "SuperUser",
    "RefreshFamily",
    "AuthAudit",
    "Tenant",
    # Módulos profesionales
    "Venta",
    "Proveedor",
    "ProveedorContacto",
    "ProveedorDireccion",
    "Compra",
    "CompraLinea",
    "Gasto",
    "CajaMovimiento",
    "CierreCaja",
    "BancoMovimiento",
    "Empleado",
    "Vacacion",
    # POS
    "POSRegister",
    "POSShift",
    "POSReceipt",
    "POSReceiptLine",
    "POSPayment",
    "StoreCredit",
    "StoreCreditEvent",
    "DocSeries",
    # IA & Notificaciones
    "Incident",
    "StockAlert",
    "NotificationChannel",
    "NotificationLog",
    # Imports
    "ImportColumnMapping",
]
