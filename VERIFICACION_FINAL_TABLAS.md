# ✅ VERIFICACIÓN FINAL: Estado de Tablas

**Fecha:** 17 Nov 2025
**Análisis completado:** Búsqueda exhaustiva en migraciones SQL
**Conclusión:** Se encontraron **11 DISCREPANCIAS CRÍTICAS** entre nombres en BD vs Modelos

---

## 🎯 HALLAZGOS PRINCIPALES

### Total de Tablas en Migraciones: **68 tablas**

**Distribución:**
- ✅ 57 tablas en INGLÉS (con nombres correctos)
- ❌ 11 tablas en ESPAÑOL (con nombres que no coinciden con modelos)

---

## 🔴 TABLAS EN ESPAÑOL (CONFLICTO)

Estas 11 tablas están creadas en BD con nombres en ESPAÑOL, pero los modelos SQLAlchemy las esperan en INGLÉS:

### 1. HR - EMPLEADOS (2 tablas)
```
BD:      empleados          ≠ Modelo: employees
BD:      vacaciones         ≠ Modelo: vacations
```
📍 Migración: `2025-11-03_180_hr_empleados`

### 2. HR - NÓMINAS (3 tablas)
```
BD:      nominas            ≠ Modelo: payrolls
BD:      nomina_conceptos   ≠ Modelo: payroll_concepts
BD:      nomina_plantillas  ≠ Modelo: payroll_templates
```
📍 Migración: `2025-11-03_201_hr_nominas`

### 3. FINANZAS - CAJA (2 tablas)
```
BD:      caja_movimientos   ≠ Modelo: cash_movements
BD:      cierres_caja       ≠ Modelo: cash_closings
```
📍 Migración: `2025-11-03_202_finance_caja`

### 4. CONTABILIDAD (3 tablas)
```
BD:      plan_cuentas       ≠ Modelo: chart_of_accounts
BD:      asientos_contables ≠ Modelo: journal_entries
BD:      asiento_lineas     ≠ Modelo: journal_entry_lines
```
📍 Migración: `2025-11-03_203_accounting`

### 5. USUARIOS/EMPRESA (1 tabla)
```
BD:      usuarios_usuarioempresa ≠ Modelo: company_users
```
📍 Migración: `2025-11-01_160_create_usuarios_usuarioempresa`

---

## ✅ TABLAS EN INGLÉS (SIN CONFLICTO)

**57 tablas con nombres CORRECTOS en inglés:**

- tenants, clients, products, product_categories, warehouses
- stock_items, stock_moves, stock_alerts
- pos_registers, pos_shifts, pos_receipts, pos_receipt_lines, pos_payments
- doc_series, store_credits, store_credit_events, pos_daily_counts
- recipes, recipe_ingredients
- production_orders, production_order_lines
- invoices, invoice_lines
- auth_user, auth_audit, auth_refresh_family, auth_refresh_token
- currencies, countries, timezones, locales, ref_timezone, ref_locale
- base_roles, core_tipoempresa, core_tiponegocio
- import_batches, import_items, import_ocr_jobs, import_column_mappings, import_mappings, import_item_corrections, import_lineage
- einv_credentials, sri_submissions, sii_batches, sii_batch_items
- notification_channels, notification_log
- incidents
- ui_templates, tenant_field_config, tenant_field_configs
- inventory_alert_configs, inventory_alert_history
- core_moneda, core_pais (Legacy)

---

## ⚠️ ACCIÓN CRÍTICA REQUERIDA

**Antes de borrar la BD, DEBES resolver esta discrepancia:**

### Opción A: Renombrar tablas en BD a INGLÉS (RECOMENDADO)

Crear nueva migración:
```
2025-11-18_001_spanish_to_english_final/
├── up.sql    (renombra todas las tablas a inglés)
└── down.sql  (rollback)
```

**Ventaja:** Los modelos ya esperan nombres en inglés, no hay cambios adicionales.

**Desventaja:** Necesita migración adicional.

### Opción B: Cambiar tablenames en modelos a ESPAÑOL

Modificar todos los `__tablename__` en:
- `app/models/finance/caja.py` - CashMovement, CashClosing
- `app/models/finance/banco.py` - BankMovement (verificar)
- `app/models/hr/empleado.py` - Empleado, Vacacion
- `app/models/hr/nomina.py` - Payroll, PayrollConcept, PayrollTemplate
- `app/models/accounting/plan_cuentas.py` - ChartOfAccounts, JournalEntry, JournalEntryLine
- `app/models/empresa/usuarioempresa.py` - CompanyUser

**Ventaja:** Mantiene consistencia con migraciones existentes.

**Desventaja:** Todos los modelos tendrán `__tablename__` en español (poco estándar).

---

## 📊 TABLA RESUMEN

| Componente | Cantidad | Conflicto | Acción |
|---|---|---|---|
| Tablas totales | 68 | - | - |
| En inglés | 57 | ✅ No | Ninguna |
| En español | 11 | ❌ Sí | **RESOLVER** |
| Migraciones | 35 | - | Ejecutar todas |
| Faltantes | ~35 | ❌ Sí | Crear migraciones |

---

## 🚀 RECOMENDACIÓN FINAL

**Ejecutar en este orden:**

1. ✅ **Crear migración de rename** (Opción A recomendada)
   - Archivo: `ops/migrations/2025-11-18_001_spanish_to_english_final/`

2. ✅ **Borrar BD completamente** (como planeabas)

3. ✅ **Re-ejecutar todas las migraciones** en orden:
   - Baseline moderno
   - Auth tables
   - Core business
   - ... todas las demás
   - **Incluir la nueva migración de rename al final**

4. ✅ **Verificar que SQLAlchemy pueda conectar**
   - Los modelos buscarán tablas con nombres en inglés
   - Con el rename, todo coincidirá

---

## 📝 PRÓXIMOS PASOS

1. ¿Cuál opción prefieres: A (Renombrar BD) o B (Cambiar modelos)?
2. Una vez decididas, te ayudo a:
   - Crear la migración faltante (si opción A)
   - O actualizar todos los modelos (si opción B)
