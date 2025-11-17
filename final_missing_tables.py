#!/usr/bin/env python3
import re
from pathlib import Path

models_dir = Path(
    r"C:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models"
)
migrations_dir = Path(
    r"C:\Users\pc_cashabamba\Documents\GitHub\proyecto\ops\migrations"
)

# Manual mapping of model names to migration table names
manual_mapping = {
    "AlertConfig": "inventory_alert_configs",
    "AlertHistory": "inventory_alert_history",
    "AuthAudit": "auth_audit",
    "BankAccount": "bank_accounts",  # might be different
    "BankMovement": "bank_movements",
    "BankTransaction": "bank_transactions",
    "BusinessCategory": "business_categories",
    "BusinessType": "business_types",
    "CashClosing": "cash_closings",
    "CashMovement": "cash_movements",
    "Cliente": "clients",
    "CompanyCategory": "company_categories",
    "CompanyModule": "company_modules",
    "CompanyRole": "base_roles",
    "CompanySettings": "company_settings",
    "CompanyUser": "company_users",
    "CompanyUserRole": "company_user_roles",
    "Country": "countries",
    "Currency": "currencies",
    "Delivery": "deliveries",
    "DocSeries": "doc_series",
    "EinvoicingCredentials": "einv_credentials",
    "Employee": "employees",
    "Expense": "expenses",
    "GlobalActionPermission": "global_action_permissions",
    "ImportAttachment": "import_attachments",
    "ImportAudit": "import_audits",
    "ImportBatch": "import_batches",
    "ImportColumnMapping": "import_column_mappings",
    "ImportItem": "import_items",
    "ImportItemCorrection": "import_item_corrections",
    "ImportLineage": "import_lineages",
    "ImportMapping": "import_mappings",
    "ImportOCRJob": "import_ocr_jobs",
    "Incident": "incidents",
    "InternalTransfer": "internal_transfers",
    "InventorySettings": "inventory_settings",
    "Invoice": "invoices",
    "InvoiceTemp": "invoice_temps",
    "JournalEntry": "journal_entries",
    "JournalEntryLine": "journal_entry_lines",
    "Language": "languages",
    "LineaFactura": "invoice_lines",
    "Module": "modules",
    "NotificationChannel": "notification_channels",
    "NotificationLog": "notification_log",
    "POSPayment": "pos_payments",
    "POSReceipt": "pos_receipts",
    "POSReceiptLine": "pos_receipt_lines",
    "POSRegister": "pos_registers",
    "POSShift": "pos_shifts",
    "Payment": "payments",
    "Payroll": "payrolls",
    "PayrollConcept": "payroll_concepts",
    "PayrollTemplate": "payroll_templates",
    "Product": "products",
    "ProductCategory": "product_categories",
    "ProductionOrder": "production_orders",
    "ProductionOrderLine": "production_order_lines",
    "Purchase": "purchases",
    "PurchaseLine": "purchase_lines",
    "RefreshFamily": "auth_refresh_family",
    "RefreshToken": "auth_refresh_token",
    "RolBase": "base_roles",
    "SIIBatch": "sii_batches",
    "SIIBatchItem": "sii_batch_items",
    "SRISubmission": "sri_submissions",
    "Sale": "sales",
    "SalesOrder": "sales_orders",
    "SalesOrderItem": "sales_order_items",
    "SectorFieldDefault": "sector_field_defaults",
    "SectorPlantilla": "sector_templates",
    "StockAlert": "stock_alerts",
    "StockItem": "stock_items",
    "StockMove": "stock_moves",
    "StoreCredit": "store_credits",
    "StoreCreditEvent": "store_credit_events",
    "SuperUser": "auth_user",
    "Supplier": "suppliers",
    "SupplierAddress": "supplier_addresses",
    "SupplierContact": "supplier_contacts",
    "Tenant": "tenants",
    "TenantFieldConfig": "tenant_field_configs",
    "TenantSettings": "tenant_settings",
    "UiTemplate": "ui_templates",
    "UserProfile": "user_profiles",
    "Vacation": "vacations",
    "Warehouse": "warehouses",
    "AssignedModule": "assigned_modules",
    "RefLocale": "locales",
    "Weekday": "weekdays",
    "BusinessHours": "business_hours",
}

# Extract table names from models
model_tables = set()
for py_file in models_dir.rglob("*.py"):
    if py_file.name == "__init__.py":
        continue
    content = py_file.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"class\s+(\w+)\(Base\)", content)
    model_tables.update(matches)

# Extract table names from migrations
migration_tables = set()
for sql_file in migrations_dir.rglob("*.sql"):
    content = sql_file.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", content)
    migration_tables.update(matches)

print("=" * 80)
print(f"Tables in models: {len(model_tables)}")
print(f"Tables in migrations: {len(migration_tables)}")
print("=" * 80)

# Find truly missing tables
missing = []
for model_name in sorted(model_tables):
    expected_table = manual_mapping.get(model_name, model_name.lower())
    if expected_table not in migration_tables:
        missing.append((model_name, expected_table))

if missing:
    print(f"\nREALLY MISSING TABLES ({len(missing)}):")
    for model_name, table_name in missing:
        print(f"  - {model_name:30} -> {table_name}")
else:
    print("\nAll tables are covered!")
