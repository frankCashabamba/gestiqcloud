# Auto-generado: registra todos los modelos importándolos

# Core models
# Sistema IA + Incidencias + Alertas
from app.models.ai import Incident, NotificationChannel, NotificationLog, StockAlert
from app.models.auth.refresh_family import RefreshFamily

# Auth & Security
from app.models.auth.useradmis import SuperUser
from app.models.company.company import (
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
    SectorTemplate,
    UserProfile,
    Weekday,
)

# Company models
from app.models.company.company_role import CompanyRole
from app.models.company.company_settings import CompanySettings, InventorySettings
from app.models.company.company_user import CompanyUser
from app.models.company.company_user_role import CompanyUserRole
from app.models.core.clients import Client, Cliente
from app.models.core.facturacion import (
    BankAccount,
    BankTransaction,
    InternalTransfer,
    Invoice,
    InvoiceTemp,
    Payment,
    TransactionStatus,
    TransactionType,
)
from app.models.core.import_audit import ImportAudit
from app.models.core.invoiceLine import BakeryLine, InvoiceLine, LineaFactura, WorkshopLine
from app.models.core.modulo import AssignedModule, CompanyModule, Module
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.core.settings import TenantSettings
from app.models.expenses import Expense
from app.models.finance import BankMovement, CashClosing, CashMovement
from app.models.hr import Employee, Vacation
from app.models.hr.payroll import Payroll, PayrollConcept, PayrollTemplate

# Imports system
from app.models.imports import ImportColumnMapping

# Inventory
from app.models.inventory.warehouse import Warehouse
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
from app.models.purchases import Purchase, PurchaseLine
from app.models.recipes import Recipe, RecipeIngredient
from app.models.sales import Sale
from app.models.security.auth_audit import AuthAudit
from app.models.suppliers import Supplier, SupplierAddress, SupplierContact
from app.models.tenant import Tenant

__all__ = [
    # Core Facturación
    "BankAccount",
    "BankTransaction",
    "InternalTransfer",
    "Invoice",
    "InvoiceTemp",
    "Payment",
    "TransactionStatus",
    "TransactionType",
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
    "TenantSettings",
    # Company
    "CompanyRole",
    "CompanySettings",
    "InventorySettings",
    "CompanyUserRole",
    "CompanyUser",
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
    "SectorTemplate",
    "BusinessType",
    "BusinessCategory",
    "UserProfile",
    # Auth & Security
    "SuperUser",
    "RefreshFamily",
    "AuthAudit",
    "Tenant",
    # Professional modules
    "Sale",
    "Supplier",
    "SupplierContact",
    "SupplierAddress",
    "Purchase",
    "PurchaseLine",
    "Expense",
    "BankMovement",
    "CashMovement",
    "CashClosing",
    "Employee",
    "Vacation",
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
    # Inventory
    "Warehouse",
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
