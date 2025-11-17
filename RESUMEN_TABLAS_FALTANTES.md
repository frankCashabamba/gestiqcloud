# RESUMEN EJECUTIVO: Tablas Faltantes para Crear

**Fecha:** 17 Nov 2025
**Estado:** Análisis completo realizado

---

## 📌 CONCLUSIÓN PRINCIPAL

Las migraciones en `ops/migrations` **crean tablas en INGLÉS**, pero **FALTAN MUCHAS TABLAS** que están definidas en los modelos de `app/models`.

**Total tablas en migraciones:** ~60 tablas
**Total tablas en modelos:** ~95 tablas
**FALTANTES:** ~35 tablas

---

## 🔴 TABLAS QUE DEFINITIVAMENTE NO EXISTEN EN BD

### Módulo: SUPPLIERS (Proveedores)
```
❌ suppliers
❌ supplier_contacts
❌ supplier_addresses
```
Motivo: Migración de rename marca explícitamente como SKIP (tabla no existe)

### Módulo: SALES (Ventas)
```
❌ sales
❌ sales_orders
❌ sales_order_items
❌ deliveries
```
Motivo: SKIP en migración

### Módulo: PURCHASES (Compras)
```
❌ purchases
❌ purchase_lines
```
Motivo: SKIP en migración

### Módulo: EXPENSES (Gastos)
```
❌ expenses
```
Motivo: SKIP en migración

### Módulo: HR (Recursos Humanos)
```
❌ vacations (Vacaciones)
```
Motivo: No creada en baseline

### Módulo: REFERENCE/CONFIG (Catálogos)
```
❌ business_types
❌ business_categories
❌ company_categories
❌ business_hours
❌ user_profiles
❌ sector_templates
❌ sector_field_defaults
```
Motivo: No mencionadas en migraciones baseline

### Módulo: IMPORT (Sistema de Importación)
```
❌ import_mappings
❌ import_item_corrections
```
Motivo: No creadas en baseline (import_column_mappings SÍ existe)

### Módulo: PAYROLL (Nómina)
```
❌ payroll_items (Podría estar como payroll_concepts)
```
Motivo: SKIP en migración de rename (nómina nunca fue creada con español)

---

## ✅ TABLAS QUE SÍ EXISTEN

### Completamente en Inglés (Baseline Moderno):
- ✅ Tenants & Multitenancy
- ✅ Products & Categories & Warehouses & Stock
- ✅ POS (Registers, Shifts, Receipts, Payments, Store Credits)
- ✅ Auth & Refresh Tokens
- ✅ Modules (Modules, Company Modules, Assigned Modules)
- ✅ Clients (Clientes)
- ✅ Invoices & Invoice Lines (invoice_lines, bakery_lines, workshop_lines)
- ✅ Recipes & Recipe Ingredients
- ✅ Production Orders
- ✅ Employees (Empleados)
- ✅ Payroll (payroll_templates, payroll_concepts, payrolls)
- ✅ Finance (cash_movements, cash_closings, bank_accounts, bank_movements, bank_transactions, payments, internal_transfers)
- ✅ Accounting (chart_of_accounts, journal_entries, journal_entry_lines)
- ✅ E-Invoicing (einv_credentials, sri_submissions, sii_batches, sii_batch_items)
- ✅ Imports (import_batches, import_items, import_attachments, import_lineage, import_ocr_jobs, import_column_mappings)
- ✅ Notifications (notification_channels, notification_log)
- ✅ Incidents & Alerts (incidents, stock_alerts)
- ✅ References (currencies, countries, languages, timezones, locales, weekdays, base_roles, global_action_permissions)
- ✅ Company Config (company_users, company_roles, company_user_roles, company_settings, company_inventory_settings)
- ✅ UI (ui_templates, tenant_field_configs)

---

## 🚀 ACCIÓN RECOMENDADA

Dado que piensas **borrar la base de datos completa**, tienes dos opciones:

### Opción A: Crear Migraciones Faltantes (Recomendado)
1. Crear archivos de migración en `ops/migrations/` para cada tabla faltante
2. Organizar por categoría:
   - `2025-11-18_300_suppliers_system`
   - `2025-11-18_310_sales_system`
   - `2025-11-18_320_purchases_system`
   - `2025-11-18_330_expenses_system`
   - `2025-11-18_340_hr_vacations`
   - `2025-11-18_350_business_reference_tables`
   - `2025-11-18_360_import_mappings`

### Opción B: Sincronizar Modelos con Migraciones
1. Eliminar de modelos las clases que no van a usar
2. O, crear todas las migraciones que faltan

---

## 📋 TABLA DE MAPEO

| Modelo | Tabla Esperada | ¿Existe? | Ubicación Migración |
|--------|---|---|---|
| BusinessType | business_types | ❌ | - |
| BusinessCategory | business_categories | ❌ | - |
| CompanyCategory | company_categories | ❌ | - |
| BusinessHours | business_hours | ❌ | - |
| UserProfile | user_profiles | ❌ | - |
| SectorPlantilla | sector_templates | ❌ | - |
| CompanySettings | company_settings | ✅ | 2025-11-17_001 |
| InventorySettings | company_inventory_settings | ✅ | 2025-11-17_001 |
| Supplier | suppliers | ❌ | - |
| SupplierContact | supplier_contacts | ❌ | - |
| SupplierAddress | supplier_addresses | ❌ | - |
| Sale | sales | ❌ | - |
| SalesOrder | sales_orders | ❌ | - |
| SalesOrderItem | sales_order_items | ❌ | - |
| Delivery | deliveries | ❌ | - |
| Purchase | purchases | ❌ | - |
| PurchaseLine | purchase_lines | ❌ | - |
| Expense | expenses | ❌ | - |
| Vacation | vacations | ❌ | - |
| ImportMapping | import_mappings | ❌ | - |
| ImportItemCorrection | import_item_corrections | ❌ | - |
| SectorFieldDefault | sector_field_defaults | ❌ | - |

---

## 💾 PRÓXIMOS PASOS

1. **Decidir:** ¿Crear migraciones para TODO o limpiar modelos?
2. **Si decides crear migraciones:**
   - Revisar definiciones de modelo para cada tabla
   - Crear SQL apropiado en inglés
   - Seguir el patrón de `up.sql` y `down.sql`

3. **Si decides limpiar modelos:**
   - Remover imports de clases sin tabla
   - Actualizar `__init__.py`
