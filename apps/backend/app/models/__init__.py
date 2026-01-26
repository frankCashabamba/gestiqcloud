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
from app.models.core.audit_event import AuditEvent
from app.models.core.country_catalogs import CountryIdType, CountryTaxCode
from app.models.core.document import Document
from app.models.core.import_audit import ImportAudit
from app.models.core.invoiceLine import BakeryLine, InvoiceLine, LineaFactura, WorkshopLine
from app.models.core.modulo import AssignedModule, CompanyModule, Module
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.company.settings import CompanySettings, InventorySettings
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
from app.models.accounting.pos_settings import TenantAccountingSettings, PaymentMethod
from app.models.printing.printer_label_configuration import PrinterLabelConfiguration

# Nuevos módulos profesionales
from app.models.production import ProductionOrder, ProductionOrderLine
from app.models.purchases import Purchase, PurchaseLine
from app.models.recipes import Recipe, RecipeIngredient
from app.models.sales.delivery import Delivery
from app.models.sales.order import SalesOrder, SalesOrderItem
from app.models.security.auth_audit import AuthAudit
from app.models.suppliers import Supplier, SupplierAddress, SupplierContact
from app.models.tenant import Tenant

# UI Configuration (Sistema Sin Hardcodes)
from app.models.core.ui_config import (
    UiSection,
    UiWidget,
    UiTable,
    UiColumn,
    UiFilter,
    UiForm,
    UiFormField,
    UiDashboard,
)

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
    "CountryIdType",
    "CountryTaxCode",
    "Document",
    "AuditEvent",
    "ImportAudit",
    "Client",
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
    "PrinterLabelConfiguration",
    # Auth & Security
    "SuperUser",
    "RefreshFamily",
    "AuthAudit",
    "Tenant",
    # Professional modules
    "SalesOrder",
    "SalesOrderItem",
    "Delivery",
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
    "TenantAccountingSettings",
    "PaymentMethod",
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
    # UI Configuration
    "UiSection",
    "UiWidget",
    "UiTable",
    "UiColumn",
    "UiFilter",
    "UiForm",
    "UiFormField",
    "UiDashboard",
]
