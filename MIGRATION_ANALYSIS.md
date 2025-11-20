# Migration vs ORM Models Analysis

## Summary
Comparing existing migrations in `ops/migrations` against ORM models defined in `apps/backend/app/models`.

---

## Tables Defined in ORM Models but NOT in Migrations

These tables are defined in SQLAlchemy ORM but don't have SQL migrations:

### Missing Core Tables:
- `auth_user` - Authentication users (baseline dependency)
- `base_roles` - Base roles
- `chart_of_accounts` - Accounting
- `company_categories` - Company settings
- `core_configuracionempresa` - Company configuration
- `core_configuracioninventarioempresa` - Inventory configuration
- `core_dia` - Days
- `core_horarioatencion` - Business hours
- `core_sectorplantilla` - Sector templates
- `banco_movimientos` - Bank movements
- `cash_closings` - Cash closings
- `cash_movements` - Cash movements
- `clients` - Clients (has migration as part of baseline)
- `compra_lineas` - Purchase lines
- `compras` - Purchases
- `deliveries` - Sales deliveries
- `doc_series` - Document series
- `einv_credentials` - eInvoicing credentials
- `employees` - HR employees
- `facturas_temp` - Temporary invoices
- `gastos` - Expenses
- `global_action_permissions` - Global permissions
- `import_attachments` - Import file attachments
- `incidents` - AI incidents
- `internal_transfers` - Stock transfers
- `invoice_lines` - Invoice lines
- `invoices` - Invoices
- `journal_entries` - Accounting journals
- `journal_entry_lines` - Journal entry lines
- `languages` - Languages
- `lineas_panaderia` - Bakery production lines
- `lineas_taller` - Workshop production lines
- `modulos_empresamodulo` - Module assignment to companies
- `modulos_modulo` - Modules
- `modulos_moduloasignado` - Module assignment to users
- `notification_channels` - Notification settings
- `notification_log` - Notification history
- `payments` - Payments
- `proveedor_contactos` - Supplier contacts
- `proveedor_direcciones` - Supplier addresses
- `proveedores` - Suppliers
- `sales_order_items` - Sales order line items
- `sales_orders` - Sales orders
- `sector_field_defaults` - Sector defaults
- `sii_batch_items` - SII batch items
- `sii_batches` - SII batches
- `store_credit_events` - Store credit transactions
- `store_credits` - Store credits
- `tenant_settings` - Tenant settings
- `user_profiles` - User profiles
- `usuarios_usuariorolempresa` - User to Company Role assignments
- `vacations` - HR vacations
- `ventas` - Sales

---

## Tables in Migrations but NOT in ORM Models

These tables exist in SQL migrations but don't have corresponding ORM models:

### Dangling Migration Tables:
- `asiento_lineas` - Accounting entry lines (alternative model)
- `asientos_contables` - Accounting entries (alternative model)
- `auth_refresh_token` - Refresh tokens (alternative to auth_refresh_family)
- `caja_movimientos` - Cash movements (Spanish name variant)
- `cierres_caja` - Cash closings (Spanish name variant)
- `plan_cuentas` - Chart of accounts (Spanish name)
- `ref_locale` - Locales reference (alternative)
- `ref_timezone` - Timezones reference (alternative)
- `tenant_field_config` - Field configs (alternative name)

---

## Tables in BOTH (Properly Migrated)

✅ These tables have both ORM models AND SQL migrations:

1. `auth_refresh_family`
2. `auth_audit`
3. `banco_movimientos`
4. `bank_accounts`
5. `bank_transactions`
6. `caja_movimientos` / `cash_movements` (dual naming)
7. `core_moneda`
8. `core_pais` / `countries` (dual)
9. `core_rolempresa` ⭐ (just migrated!)
10. `core_tipoempresa`
11. `core_tiponegocio`
12. `currencies`
13. `empleados` / `employees` (dual)
14. `import_batches`
15. `import_column_mappings`
16. `import_item_corrections`
17. `import_items`
18. `import_lineage`
19. `import_mappings`
20. `import_ocr_jobs`
21. `inventory_alert_configs`
22. `inventory_alert_history`
23. `locales`
24. `nomina_conceptos`
25. `nomina_plantillas`
26. `nominas`
27. `pos_daily_counts`
28. `pos_payments`
29. `pos_receipt_lines`
30. `pos_receipts`
31. `pos_registers`
32. `pos_shifts`
33. `product_categories`
34. `production_order_lines`
35. `production_orders`
36. `products`
37. `recipe_ingredients`
38. `recipes`
39. `sri_submissions`
40. `stock_alerts`
41. `stock_items`
42. `stock_moves`
43. `tenant_field_configs` / `tenant_field_config` (dual)
44. `tenants`
45. `timezones`
46. `ui_templates`
47. `usuarios_usuarioempresa`
48. `warehouses`

---

## Issues & Recommendations

### 🔴 Critical Issues:

1. **Missing Core Tables in Migrations** (~35+ tables)
   - Many essential ORM models lack SQL migrations
   - This means tables are only created if ORM generates them
   - Not compatible with pure SQL deployment strategy

2. **Dual/Inconsistent Naming**
   - Some tables have both Spanish and English names
   - Example: `caja_movimientos` vs `cash_movements`
   - Example: `plan_cuentas` vs `chart_of_accounts`

3. **Migration Table Without ORM Model**
   - `asiento_lineas`, `asientos_contables` exist in migrations but not in models
   - May be legacy or planned features

### 🟡 Medium Priority:

1. **Foreign Key References**
   - Need to verify all FK references work correctly
   - Especially problematic if referencing non-existent tables

2. **RLS Policies**
   - Some migrations create RLS policies, others don't
   - Should be consistent

### 🟢 Recommendations:

1. **Phase 1: Audit Foreign Keys**
   - Review all FK references in migrations
   - Ensure target tables exist

2. **Phase 2: Standardize Naming**
   - Choose consistent naming convention (English)
   - Create migrations to rename dual-named tables

3. **Phase 3: Complete Migration Coverage**
   - Generate migrations for all ORM models missing them
   - Use `alembic revision --autogenerate` or manual creation

4. **Phase 4: Documentation**
   - Document table naming conventions
   - Create table mapping guide (ORM ↔ SQL)

---

## Action Items for RolEmpresa

✅ **COMPLETED:**
- Created migration: `2025-11-17_800_rolempresas_to_english`
- Renamed columns: `nombre` → `name`, `descripcion` → `description`, `permisos` → `permissions`, `creado_por_empresa` → `created_by_company`
- Updated ORM model, schemas, routes, services
- Applied migration to database

⚠️ **PENDING:**
- Test all API endpoints using new field names
- Verify RLS policies work correctly
- Check for any remaining SQL queries using old column names

---

## Database Connection Status

**Last Migration Run:** 2025-11-17
**Status:** ✅ All 25 migrations applied (before RolEmpresa was added)
**Current Count:** 26 migrations total
**Database:** gestiqclouddb_dev (PostgreSQL)
