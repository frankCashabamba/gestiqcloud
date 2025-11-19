# Auto-generado: registra todos los modelos importándolos

# Core models
# Sistema IA + Incidencias + Alertas
from app.models.ai import Incident, NotificationChannel, NotificationLog, StockAlert
from app.models.auth.refresh_family import RefreshFamily

# Auth & Security
from app.models.auth.useradmis import SuperUser
from app.models.core.auditoria_importacion import ImportAudit
from app.models.core.clients import Client, Cliente
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
from app.models.core.invoiceLine import BakeryLine, InvoiceLine, LineaFactura, WorkshopLine
from app.models.core.modulo import AssignedModule, CompanyModule, Module
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.core.settings import TenantSettings
from app.models.empresa.empresa import (
    BusinessCategory,
    BusinessHours,
    BusinessType,
    CompanyCategory,
    Country,
    Currency,
    GlobalActionPermission,
    Language,
    RefLocale,
    RefTimezone,
    RolBase,
    SectorPlantilla,
    UserProfile,
    Weekday,
)

# Empresa (legacy)
from app.models.empresa.rolempresas import CompanyRole
from app.models.empresa.settings import CompanySettings, InventorySettings
from app.models.empresa.usuario_rolempresa import CompanyUserRole
from app.models.empresa.usuarioempresa import CompanyUser, UsuarioEmpresa
from app.models.expenses import Expense, Gasto
from app.models.finance import BancoMovimiento, BankMovement, CajaMovimiento, CierreCaja
from app.models.hr import Empleado, Vacacion
from app.models.hr.nomina import Payroll, PayrollConcept, PayrollTemplate

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

# Nuevos módulos profesionales
from app.models.production import ProductionOrder, ProductionOrderLine
from app.models.purchases import Compra, CompraLinea, Purchase, PurchaseLine
from app.models.recipes import Recipe, RecipeIngredient
from app.models.sales import Sale, Venta
from app.models.security.auth_audit import AuthAudit
from app.models.suppliers import (
    Proveedor,
    ProveedorContacto,
    ProveedorDireccion,
    Supplier,
    SupplierAddress,
    SupplierContact,
)
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
    "InvoiceLine",
    "LineaFactura",
    "BakeryLine",
    "WorkshopLine",
    # Core Models
    "Module",
    "CompanyModule",
    "AssignedModule",
    "Product",
    "Recipe",
    "RecipeIngredient",
    "ProductCategory",
    "ImportAudit",
    "Client",
    "Cliente",
    "TenantSettings",
    # Empresa
    "CompanyRole",
    "CompanySettings",
    "InventorySettings",
    "CompanyUserRole",
    "CompanyUser",
    "UsuarioEmpresa",
    "CompanyCategory",
    "Weekday",
    "GlobalActionPermission",
    "BusinessHours",
    "Language",
    "Currency",
    "Country",
    "RefTimezone",
    "RefLocale",
    "RolBase",
    "SectorPlantilla",
    "BusinessType",
    "BusinessCategory",
    "UserProfile",
    # Auth & Security
    "SuperUser",
    "RefreshFamily",
    "AuthAudit",
    "Tenant",
    # Módulos profesionales
    "Sale",
    "Supplier",
    "SupplierContact",
    "SupplierAddress",
    "Purchase",
    "PurchaseLine",
    "Expense",
    "CajaMovimiento",
    "CierreCaja",
    "BankMovement",
    "Empleado",
    "Vacacion",
    # Backward compatibility aliases
    "Venta",
    "Proveedor",
    "ProveedorContacto",
    "ProveedorDireccion",
    "Compra",
    "CompraLinea",
    "Gasto",
    "BancoMovimiento",
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
    # Payroll
    "Payroll",
    "PayrollConcept",
    "PayrollTemplate",
    # Production
    "ProductionOrder",
    "ProductionOrderLine",
]
