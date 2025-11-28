# Modelos y entidades clave (resumen)

## Comunes
- `tenant_id` en tablas de negocio para multitenancy.
- Campos audit: `created_at`, `updated_at` donde aplique.

## Ejemplos por módulo
- Products: `products` (sku, name, price, stock, unit, categoria), `product_categories`.
- Sales/POS: `sales_orders`, `sales_order_lines`, `pos_receipts`, `pos_receipt_lines`, `pos_payments`.
- Purchases: `purchases`, `purchase_lines`.
- Expenses: `expenses`.
- Finanzas: `cash_boxes`, `cash_movements`, `bank_accounts`, `bank_transactions`.
- Accounting: `accounts`/`plan`, `journal_entries`, `journal_lines`.
- Invoicing: `invoices`, `invoice_lines` (no electrónica), plantillas PDF/HTML.
- Einvoicing: `invoices`/`invoices_temp` con datos para SRI/Facturae.
- Inventario: `stock_items`, `stock_moves`, `stock_alerts`.
- Production: `production_orders`, `production_order_lines`, `recipes`, `recipe_ingredients`.
- Suppliers: `suppliers`, `supplier_contacts`, `supplier_addresses`.
- Clients/CRM: `clients`, `leads`, `opportunities`.
- Settings/Modulos: `modules`, `company_modules`, `assigned_modules`, `tenant_settings`, `tenant_module_settings`, `tenant_field_config`, `sector_field_defaults`.
- Registry/Company: `companies/tenants` y relaciones con módulos y settings.
- Imports: `import_batches`, `import_items`, `import_mappings`, `import_item_corrections`, `import_lineage`, `auditoria_importacion` (batch_id/item_id).
- Payments: `pos_payments` y tablas por proveedor si existen.

## Notas
- Consultar modelos concretos en `app/models` y `app/db/models.py` para campos exactos y relaciones.
- Revisar RLS/tenant_id antes de alterar estructuras.
- Alembic refleja cambios estructurales; migraciones manuales en `ops/migrations` pueden contener snapshots.
