# Estado de Migraciones de Base de Datos

## Resumen Ejecutivo
- **Tablas Requeridas (ORM):** 65
- **Migraciones Existentes:** 28
- **Estado Actual:** Parcialmente completado

## Estructura de Migraciones

### ✅ Migraciones Baseline Completadas (2025-11-01)

#### `000_baseline_modern`
Crea el esquema base completo:
- tenants
- product_categories
- products
- suppliers (proveedores)
- clients
- warehouses
- inventory (stock_items, stock_moves)
- auth_refresh_token, auth_refresh_family
- Y muchas más...

#### `100_auth_tables` ⭐ NUEVA
Crea tablas de autenticación faltantes:
- auth_user (superadmin/system users)
- auth_audit (authentication events log)

#### `001_catalog_tables`
Tablas de catálogo y referencia:
- Datos de inicialización
- Configuraciones estándar

#### `150_modulos_to_english`
Placeholder para módulos en inglés

#### `160_create_usuarios_usuarioempresa`
- usuarios_usuarioempresa
- Configuraciones de usuario-empresa

#### `170_reference_tables`
Tablas de referencia:
- Timezones
- Locales
- Divisas
- Etc.

#### `170_tenant_field_config`
Configuraciones de campos por tenant

#### `171_ref_timezones_locales`
Referencia de zonas horarias y locales

#### `172_core_moneda_catalog`
Catálogo de monedas

#### `173_core_country_catalog`
Catálogo de países

### ✅ Migraciones de Funcionalidad (2025-11-02 a 2025-11-07)

| Migración | Tablas Creadas | Estado |
|-----------|---|---|
| **231_product_categories_add_metadata** | ALTER product_categories | ✅ |
| **300_import_batches_system** | import_batches, import_items, import_attachments, import_mappings, import_item_corrections, import_lineage, import_ocr_jobs | ✅ |
| **400_import_column_mappings** | import_column_mappings | ✅ |
| **050_create_recipes_tables** | recipes, recipe_ingredients | ✅ |
| **180_hr_empleados** | employees, vacations | ✅ |
| **200_add_recipe_computed_columns** | ALTER recipes | ✅ |
| **200_production_orders** | production_orders, production_order_lines | ✅ |
| **201_add_unit_conversion** | unit_conversions | ✅ |
| **201_hr_nominas** | payrolls, nomina_conceptos, nomina_plantillas | ✅ |
| **202_finance_caja** | cash_movements, cash_closings | ✅ |
| **203_accounting** | chart_of_accounts, journal_entries, journal_entry_lines | ✅ |
| **240_ui_templates_catalog** | ui_templates | ✅ |
| **fix_negative_stock_alerts** | inventory_alert_configs, inventory_alert_history | ✅ |
| **500_pos_daily_counts** | pos_registers, pos_shifts, pos_receipts, pos_receipt_lines, pos_payments | ✅ |
| **600_inventory_alerts** | ALTER inventory_alert_* | ✅ |

### ✅ Migraciones de Renombre (2025-11-17)

| Migración | Cambios | Estado |
|-----------|---|---|
| **001_spanish_to_english_names** | Renombra todas las tablas y columnas de español a inglés | ✅ COMPLETADO |
| **800_rolempresas_to_english** | Renombra core_rolempresa → company_roles | ✅ COMPLETADO |

### ✅ Migraciones Adicionales (2025-01-11)

| Migración | Cambios | Estado |
|-----------|---|---|
| **001_add_classification_fields** | Agrega campos a import_batches para clasificación AI | ✅ |

---

## Mapeo de Tablas por Migración

### Tablas Creadas ✅

```
Tenants & Core:
  - tenants (000_baseline_modern)
  - tenant_settings
  - tenant_field_configs (170_tenant_field_config)

Autenticación:
  - auth_user (100_auth_tables) ⭐ NUEVA
  - auth_refresh_token (000_baseline_modern)
  - auth_refresh_family (000_baseline_modern)
  - auth_audit (100_auth_tables) ⭐ NUEVA

Catálogos:
  - product_categories (000_baseline_modern)
  - products (000_baseline_modern)
  - doc_series

Proveedores (Suppliers):
  - suppliers (000_baseline_modern) [was: proveedores]
  - supplier_contacts (000_baseline_modern) [was: proveedor_contactos]
  - supplier_addresses (000_baseline_modern) [was: proveedor_direcciones]

Clientes:
  - clients (000_baseline_modern)

Almacén:
  - warehouses (000_baseline_modern)
  - stock_items (000_baseline_modern)
  - stock_moves (000_baseline_modern)

Compras:
  - purchases [was: compras] (renombrado en 001_spanish_to_english_names)
  - purchase_lines [was: compra_lineas] (renombrado en 001_spanish_to_english_names)

Ventas:
  - sales [was: ventas] (renombrado en 001_spanish_to_english_names)
  - sales_orders
  - sales_order_items
  - deliveries

Gastos:
  - expenses [was: gastos] (renombrado en 001_spanish_to_english_names)

Finanzas:
  - bank_movements [was: banco_movimientos] (renombrado en 001_spanish_to_english_names)
  - bank_accounts
  - bank_transactions
  - payments
  - internal_transfers
  - cash_movements (202_finance_caja)
  - cash_closings (202_finance_caja)

Contabilidad:
  - chart_of_accounts (203_accounting)
  - journal_entries (203_accounting)
  - journal_entry_lines (203_accounting)

RR.HH:
  - employees (180_hr_empleados)
  - vacations (180_hr_empleados)
  - payrolls [was: nominas] (201_hr_nominas) [renombrado en 001_spanish_to_english_names]
  - nomina_conceptos [was] → payroll_items (201_hr_nominas) [renombrado en 001_spanish_to_english_names]
  - nomina_plantillas [was] → payroll_templates (201_hr_nominas) [renombrado en 001_spanish_to_english_names]

Importaciones:
  - import_batches (300_import_batches_system)
  - import_items (300_import_batches_system)
  - import_attachments (300_import_batches_system)
  - import_mappings (300_import_batches_system)
  - import_item_corrections (300_import_batches_system)
  - import_lineage (300_import_batches_system)
  - import_ocr_jobs (300_import_batches_system)
  - import_column_mappings (400_import_column_mappings)

Recetas:
  - recipes (050_create_recipes_tables)
  - recipe_ingredients (050_create_recipes_tables)

Producción:
  - production_orders (200_production_orders)
  - production_order_lines (200_production_orders)

POS (Punto de Venta):
  - pos_registers (500_pos_daily_counts)
  - pos_shifts (500_pos_daily_counts)
  - pos_receipts (500_pos_daily_counts)
  - pos_receipt_lines (500_pos_daily_counts)
  - pos_payments (500_pos_daily_counts)
  - store_credits
  - store_credit_events

Módulos:
  - modulos_modulo (000_baseline_modern) [renombrado a modules]
  - modulos_empresamodulo (000_baseline_modern) [renombrado a company_modules]
  - modulos_moduloasignado (000_baseline_modern) [renombrado a assigned_modules]

Empresa/Config:
  - core_tipoempresa [renombrado a company_types]
  - core_tiponegocio [renombrado a business_types]
  - core_rolempresa [renombrado a company_roles] (800_rolempresas_to_english)
  - core_configuracionempresa [renombrado a company_settings]
  - core_configuracioninventarioempresa [renombrado a company_inventory_settings]
  - usuarios_usuarioempresa [renombrado a user_companies] (160_create_usuarios_usuarioempresa)
  - usuarios_usuariorolempresa [renombrado a user_company_roles]

Alertas:
  - inventory_alert_configs (fix_negative_stock_alerts)
  - inventory_alert_history (fix_negative_stock_alerts)

UI:
  - ui_templates (240_ui_templates_catalog)
  - tenant_field_configs (170_tenant_field_config)
  - sector_field_defaults

Otros:
  - auditoria_importacion [renombrado a import_audit]
  - invoices [was: facturas]
  - invoice_lines [was: lineas_factura]
  - invoices_temp [was: facturas_temp] (renombrado)
  - bakery_lines [was: lineas_panaderia] (renombrado)
  - workshop_lines [was: lineas_taller] (renombrado)
  - incidents
  - notification_channels
  - notification_log
  - einv_credentials
  - sri_submissions
  - sii_batches
  - sii_batch_items
```

---

## Comando para Ejecutar Todas las Migraciones

```bash
cd /path/to/proyecto
python ops/scripts/migrate_all_migrations.py --database-url "postgresql://user:password@localhost:5432/database"
```

O con variables de entorno:
```bash
export DATABASE_URL="postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
python ops/scripts/migrate_all_migrations.py
```

---

## Próximos Pasos

### 1. Ejecutar Migraciones
```bash
python ops/scripts/migrate_all_migrations.py --database-url "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
```

### 2. Validar Esquema
```bash
psql -h localhost -d gestiqclouddb_dev -c "\dt" # Lista todas las tablas
psql -h localhost -d gestiqclouddb_dev -c "\d suppliers" # Inspecciona una tabla
```

### 3. Actualizar Código Python
- [ ] Revisar `/app/schemas/` - Pydantic models
- [ ] Revisar `/app/services/` - Lógica de negocio
- [ ] Revisar `/app/routers/` - Endpoints API
- [ ] Actualizar SQL queries en servicios

### 4. Ejecutar Tests
```bash
pytest tests/ -v
```

### 5. Verificar Integridad
```bash
# En psql:
\d suppliers
\d purchases
\d expenses
\d payrolls
```

---

## Notas Importantes

- **Migraciones son idempotentes**: Pueden ejecutarse múltiples veces sin problemas (usan `IF NOT EXISTS`)
- **Rollback**: Revisar archivos `down.sql` en cada carpeta de migración
- **Orden**: Las migraciones se ejecutan en orden numérico/alfabético
- **Baseline**: `000_baseline_modern` debe ejecutarse primero (crea tablas base)
- **Renombres**: Las migraciones `001_spanish_to_english_names` renombran tablas existentes

---

## Referencia Rápida de Tablas Renombradas

| Antes (Español) | Ahora (Inglés) | Migración |
|---|---|---|
| proveedores | suppliers | 000_baseline_modern → 001_spanish_to_english_names |
| proveedor_contactos | supplier_contacts | 000_baseline_modern → 001_spanish_to_english_names |
| proveedor_direcciones | supplier_addresses | 000_baseline_modern → 001_spanish_to_english_names |
| compras | purchases | 000_baseline_modern → 001_spanish_to_english_names |
| compra_lineas | purchase_lines | 000_baseline_modern → 001_spanish_to_english_names |
| ventas | sales | 000_baseline_modern → 001_spanish_to_english_names |
| gastos | expenses | 000_baseline_modern → 001_spanish_to_english_names |
| banco_movimientos | bank_movements | 000_baseline_modern → 001_spanish_to_english_names |
| nominas | payrolls | 201_hr_nominas → 001_spanish_to_english_names |
| nomina_conceptos | payroll_items | 201_hr_nominas → 001_spanish_to_english_names |
| nomina_plantillas | payroll_templates | 201_hr_nominas → 001_spanish_to_english_names |
| modulos_modulo | modules | 000_baseline_modern → 001_spanish_to_english_names |
| modulos_empresamodulo | company_modules | 000_baseline_modern → 001_spanish_to_english_names |
| modulos_moduloasignado | assigned_modules | 000_baseline_modern → 001_spanish_to_english_names |
| usuarios_usuarioempresa | user_companies | 160_create_usuarios_usuarioempresa → 001_spanish_to_english_names |
| usuarios_usuariorolempresa | user_company_roles | 000_baseline_modern → 001_spanish_to_english_names |
| core_configuracionempresa | company_settings | 000_baseline_modern → 001_spanish_to_english_names |
| core_configuracioninventarioempresa | company_inventory_settings | 000_baseline_modern → 001_spanish_to_english_names |
| core_rolempresa | company_roles | 800_rolempresas_to_english |
| core_tipoempresa | company_types | 000_baseline_modern → 001_spanish_to_english_names |
| core_tiponegocio | business_types | 000_baseline_modern → 001_spanish_to_english_names |
| core_moneda | currencies_legacy | 000_baseline_modern → 001_spanish_to_english_names |
| lineas_panaderia | bakery_lines | 000_baseline_modern → 001_spanish_to_english_names |
| lineas_taller | workshop_lines | 000_baseline_modern → 001_spanish_to_english_names |
| facturas_temp | invoices_temp | 000_baseline_modern → 001_spanish_to_english_names |
| auditoria_importacion | import_audit | 000_baseline_modern → 001_spanish_to_english_names |
