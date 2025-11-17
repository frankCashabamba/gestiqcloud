# Análisis Comparativo: Modelos vs Migraciones Existentes

**Fecha:** 17 Nov 2025
**Estado:** Revisión de qué tablas están en migraciones SQL y qué falta

---

## 📊 TABLAS ENCONTRADAS EN MIGRACIONES SQL

### Baseline Moderno (2025-11-01_000_baseline_modern)
✅ **Tablas Core:**
- `tenants` - Entidades multi-tenant principales
- `product_categories` - Categorías de productos
- `products` - Productos
- `warehouses` - Almacenes
- `stock_items` - Items de inventario
- `stock_moves` - Movimientos de stock
- `stock_alerts` - Alertas de stock
- `pos_registers` - Registros POS
- `pos_shifts` - Turnos POS
- `pos_receipts` - Recibos POS
- `pos_receipt_lines` - Líneas de recibos POS
- `pos_payments` - Pagos POS
- `auth_refresh_family` - Familias de refresh tokens
- `auth_refresh_token` - Refresh tokens

### Auth Tables (2025-11-01_100_auth_tables)
✅ **Tablas de Autenticación:**
- `auth_user` - Usuarios de administración (SuperUser)
- `auth_audit` - Auditoría de autenticación

### Core Business (2025-11-01_110_core_business_tables)
✅ **Tablas de Negocio:**
- `clients` - Clientes/Proveedores
- `invoices` - Facturas
- `invoice_lines` - Líneas de factura

### Config Tables (2025-11-01_120_config_tables)
✅ **Tablas de Configuración:**
- `tenant_settings` - Configuración de tenants

### POS Extensions (2025-11-01_130_pos_extensions)
✅ **Extensiones POS:**
- `doc_series` - Series de documentos
- `store_credits` - Créditos de tienda
- `store_credit_events` - Eventos de créditos

### E-Invoicing (2025-11-01_140_einvoicing_tables)
✅ **Tablas E-Invoicing:**
- `einv_credentials` - Credenciales e-invoicing
- `sri_submissions` - Envíos SRI (Ecuador)
- `sii_batches` - Lotes SII (España)
- `sii_batch_items` - Items de lotes SII

### AI & Incidents (2025-11-01_150_ai_incident_tables)
✅ **Tablas IA:**
- `incidents` - Incidentes
- `notification_channels` - Canales de notificación
- `notification_log` - Log de notificaciones

### Modules (2025-11-01_150_modulos_to_english)
✅ **Tabla de Módulos:**
- `modules` - Módulos del sistema
- `company_modules` - Módulos asignados a empresas
- `assigned_modules` - Módulos asignados

### Users & Company (2025-11-01_160_create_usuarios_usuarioempresa)
✅ **Tablas de Usuarios y Empresa:**
- `company_users` - Usuarios de empresa
- `company_roles` - Roles de empresa
- `company_user_roles` - Roles de usuario en empresa

### Reference Tables (2025-11-01_170_reference_tables)
✅ **Tablas de Referencia:**
- `languages` - Idiomas
- `weekdays` - Días de la semana
- `global_action_permissions` - Permisos globales
- `base_roles` - Roles base

### Tenant Field Config (2025-11-01_170_tenant_field_config)
✅ **Configuración de Campos:**
- `tenant_field_configs` - Configuración de campos por tenant

### Timezones & Locales (2025-11-01_171_ref_timezones_locales)
✅ **Zonas Horarias y Locales:**
- `timezones` - Zonas horarias (ref_timezone)
- `locales` - Locales (ref_locale)

### Core Catalogs (2025-11-01_172_core_moneda_catalog, 2025-11-01_173_core_country_catalog)
✅ **Catálogos:**
- `currencies` - Monedas
- `countries` - Países

### Product Categories Metadata (2025-11-02_231_product_categories_add_metadata)
✅ **Extensión de categorías**

### Import System (2025-11-02_300_import_batches_system, 2025-11-02_400_import_column_mappings)
✅ **Tablas de Importación:**
- `import_batches` - Lotes de importación
- `import_items` - Items importados
- `import_attachments` - Adjuntos de importación
- `import_lineage` - Linaje de importación
- `import_ocr_jobs` - Trabajos OCR
- `import_column_mappings` - Mapeos de columnas

### Recipes (2025-11-03_050_create_recipes_tables)
✅ **Tablas de Recetas:**
- `recipes` - Recetas
- `recipe_ingredients` - Ingredientes de recetas

### HR (2025-11-03_180_hr_empleados)
✅ **Recursos Humanos:**
- `employees` - Empleados

### Production (2025-11-03_200_production_orders)
✅ **Producción:**
- `production_orders` - Órdenes de producción
- `production_order_lines` - Líneas de órdenes

### Unit Conversion (2025-11-03_201_add_unit_conversion)
✅ **Conversión de Unidades:**
- `unit_conversions` - Conversiones entre unidades

### HR Payroll (2025-11-03_201_hr_nominas)
✅ **Nómina:**
- `payroll_templates` - Plantillas de nómina
- `payroll_concepts` - Conceptos de nómina
- `payrolls` - Nóminas

### Finance Cash (2025-11-03_202_finance_caja)
✅ **Finanzas/Caja:**
- `cash_movements` - Movimientos de caja
- `cash_closings` - Cierres de caja
- `bank_movements` - Movimientos bancarios
- `bank_accounts` - Cuentas bancarias
- `bank_transactions` - Transacciones bancarias
- `payments` - Pagos
- `internal_transfers` - Transferencias internas

### Accounting (2025-11-03_203_accounting)
✅ **Contabilidad:**
- `chart_of_accounts` - Plan de cuentas
- `journal_entries` - Asientos de diario
- `journal_entry_lines` - Líneas de asientos

### UI Templates (2025-11-04_240_ui_templates_catalog)
✅ **Plantillas UI:**
- `ui_templates` - Plantillas UI

### POS Daily Counts (2025-11-06_500_pos_daily_counts)
✅ **POS:**
- `pos_daily_counts` - Conteos diarios POS

### Inventory Alerts (2025-11-07_600_inventory_alerts)
✅ Mejoras a alertas de stock

### Spanish to English Names (2025-11-17_001_spanish_to_english_names)
✅ Renombres de tablas y columnas a inglés

### Company Settings (2025-11-17_800_rolempresas_to_english)
✅ Renombres company_settings e inventory_settings

---

## 🔍 ANÁLISIS DETALLADO DE MIGRACIONES (Spanish to English)

Según **2025-11-17_001_spanish_to_english_names**:

### ✅ RENOMBRADAS EXITOSAMENTE:
- `auditoria_importacion` → `import_audit`
- `lineas_panaderia` → `bakery_lines`
- `lineas_taller` → `workshop_lines`
- `facturas_temp` → `invoices_temp`
- `modulos_modulo` → `modules`
- `modulos_empresamodulo` → `company_modules`
- `modulos_moduloasignado` → `assigned_modules`
- `usuarios_usuariorolempresa` → `user_company_roles`
- `core_configuracionempresa` → `company_settings`
- `core_configuracioninventarioempresa` → `company_inventory_settings`
- `core_rolempresa` → `company_roles`

### ⏭️ MARCADAS COMO SKIP (No existen en baseline):
Los siguientes comentarios en la migración indican que **NUNCA fueron creadas en baseline**:
- `proveedores` → `suppliers` (NO EXISTE)
- `ventas` → `sales` (NO EXISTE)
- `compras` → `purchases` (NO EXISTE)
- `compra_lineas` → `purchase_lines` (NO EXISTE)
- `gastos` → `expenses` (NO EXISTE)
- `banco_movimientos` → `bank_movements` (Podría existir como `bank_movements` en baseline)
- `nominas` → `payrolls` (Podría existir como `payrolls` en baseline)
- `nomina_conceptos` → `payroll_items` (NO EXISTE)
- `nomina_plantillas` → `payroll_templates` (Podría existir en baseline)

## 🔴 TABLAS FALTANTES (NO EN MIGRACIONES)

### Definitivamente NO existen:
❌ `suppliers` - Supplier
❌ `supplier_contacts` - SupplierContact
❌ `supplier_addresses` - SupplierAddress
❌ `sales` - Sale
❌ `sales_orders` - SalesOrder
❌ `sales_order_items` - SalesOrderItem
❌ `deliveries` - Delivery
❌ `purchases` - Purchase
❌ `purchase_lines` - PurchaseLine
❌ `expenses` - Expense
❌ `vacations` - Vacation
❌ `import_mappings` - ImportMapping
❌ `import_item_corrections` - ImportItemCorrection

### Parcialmente creadas o inciertas:
❓ `business_types` - BusinessType (Mencionado en comentario como skip)
❓ `business_categories` - BusinessCategory
❓ `company_categories` - CompanyCategory
❓ `business_hours` - BusinessHours
❓ `user_profiles` - UserProfile
❓ `sector_templates` - SectorPlantilla
❓ `payroll_templates` - PayrollTemplate
❓ `payroll_items` - Podría estar como payroll_concepts (CREADA EN BASELINE)
❓ `sector_field_defaults` - SectorFieldDefault
❓ `bank_movements` - Podría estar en finance (VERIFICAR)

---

## 📋 MODELOS POR CATEGORÍA

### ✅ YA EXISTENTES (Confirmados)
- Tenants
- Products & Categories
- Inventory (Warehouses, Stock Items, Stock Moves)
- POS System (Registers, Shifts, Receipts, Payments, Store Credits)
- Authentication (Auth User, Refresh Tokens, Auth Audit)
- Modules (Modules, Company Modules, Assigned Modules)
- Clients
- Invoices & Invoice Lines
- Currencies, Countries, Languages
- Timezones, Locales
- Recipes & Recipe Ingredients
- Production Orders
- Employees
- Payroll (Templates, Concepts, Payrolls)
- Finance (Cash Movements, Bank Movements, Bank Accounts, Transactions, Payments)
- Accounting (Chart of Accounts, Journal Entries)
- E-Invoicing (Credentials, SRI Submissions, SII Batches)
- Import System (Batches, Items, Attachments, Mappings, OCR)
- Notifications (Channels, Logs)
- Incidents
- UI Templates

### ❌ FALTANTES (NO Encontrados)
- Business Type/Category (Catálogos)
- Company Category
- Business Hours
- User Profiles
- Sector Templates
- Company Settings (parcial)
- Inventory Settings (parcial)
- Specialized Invoice Lines (Bakery, Workshop)
- Sales Orders & Items
- Deliveries
- Purchases & Purchase Lines
- Suppliers & Supplier Contacts/Addresses
- Sales
- Vacations
- Expenses
- Import Item Corrections
- Sector Field Defaults

---

## 🎯 RECOMENDACIONES

1. **Revisar tablas renombradas:** Algunas tablas con nombre en español pueden estar bajo otro nombre en inglés
2. **Tablas heredadas:** Compra, Venta, Proveedor, Gasto pueden ser alias/legacy de nombres en inglés
3. **Crear migraciones faltantes** para las tablas que no están en ops/migrations
4. **Normalizar nombres** de tablas a inglés consistentemente

---

## ✅ PRÓXIMOS PASOS

1. Revisar migraciones `2025-11-17_001_spanish_to_english_names` para ver qué renombres se hicieron
2. Buscar tablas con nombres en español que aún existan
3. Crear migraciones para tablas faltantes
4. Sincronizar modelos con migraciones
