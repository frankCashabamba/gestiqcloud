# Tablas REALES en Base de Datos (Verificadas en Migraciones)

**Fecha:** 17 Nov 2025
**Estado:** Análisis completado con búsqueda exhaustiva en migraciones SQL

---

## ⚠️ HALLAZGO CRÍTICO

**Se encontraron 11 TABLAS CON NOMBRES EN ESPAÑOL** que todavía existen en las migraciones:

### 🔴 TABLAS EN ESPAÑOL (AÚN EXISTEN):
```
❌ empleados          (2025-11-03_180_hr_empleados)
❌ vacaciones         (2025-11-03_180_hr_empleados)
❌ nominas            (2025-11-03_201_hr_nominas)
❌ nomina_conceptos   (2025-11-03_201_hr_nominas)
❌ nomina_plantillas  (2025-11-03_201_hr_nominas)
❌ caja_movimientos   (2025-11-03_202_finance_caja)
❌ cierres_caja       (2025-11-03_202_finance_caja)
❌ plan_cuentas       (2025-11-03_203_accounting)
❌ asientos_contables (2025-11-03_203_accounting)
❌ asiento_lineas     (2025-11-03_203_accounting)
```

**IMPORTANTE:** Estos nombres de tabla en ESPAÑOL pueden causar conflictos porque los modelos de SQLAlchemy esperan nombres en INGLÉS.

---

## ✅ LISTA COMPLETA DE TABLAS CREADAS EN BD (68 tablas)

### AUTENTICACIÓN (4):
- ✅ auth_user
- ✅ auth_audit
- ✅ auth_refresh_family
- ✅ auth_refresh_token

### CATÁLOGOS & REFERENCIAS (9):
- ✅ currencies
- ✅ countries
- ✅ timezones
- ✅ locales
- ✅ ref_timezone
- ✅ ref_locale
- ✅ base_roles
- ✅ core_tipoempresa
- ✅ core_tiponegocio

### CORE BUSINESS (3):
- ✅ tenants
- ✅ clients
- ✅ core_moneda (Legacy, debería ser currencies)
- ✅ core_pais (Legacy, debería ser countries)

### PRODUCTOS & INVENTARIO (5):
- ✅ products
- ✅ product_categories
- ✅ warehouses
- ✅ stock_items
- ✅ stock_moves

### ALERTAS (3):
- ✅ stock_alerts
- ✅ inventory_alert_configs
- ✅ inventory_alert_history

### FACTURACIÓN (2):
- ✅ invoices
- ✅ invoice_lines

### NÓMINA (3) - EN ESPAÑOL:
- ❌ nominas
- ❌ nomina_conceptos
- ❌ nomina_plantillas

### HR (2) - EN ESPAÑOL:
- ❌ empleados
- ❌ vacaciones

### FINANZAS/CAJA (2) - EN ESPAÑOL:
- ❌ caja_movimientos
- ❌ cierres_caja

### CONTABILIDAD (3) - EN ESPAÑOL:
- ❌ plan_cuentas
- ❌ asientos_contables
- ❌ asiento_lineas

### POS (5):
- ✅ pos_registers
- ✅ pos_shifts
- ✅ pos_receipts
- ✅ pos_receipt_lines
- ✅ pos_payments
- ✅ doc_series
- ✅ store_credits
- ✅ store_credit_events
- ✅ pos_daily_counts

### RECETAS (2):
- ✅ recipes
- ✅ recipe_ingredients

### PRODUCCIÓN (2):
- ✅ production_orders
- ✅ production_order_lines

### E-INVOICING (3):
- ✅ einv_credentials
- ✅ sri_submissions
- ✅ sii_batches
- ✅ sii_batch_items

### IMPORTACIÓN (5):
- ✅ import_batches
- ✅ import_items
- ✅ import_ocr_jobs
- ✅ import_column_mappings
- ✅ import_mappings
- ✅ import_item_corrections
- ✅ import_lineage (Puede ser import_lineage, verificar)

### NOTIFICACIONES (2):
- ✅ notification_channels
- ✅ notification_log

### INCIDENTES (1):
- ✅ incidents

### UI/CONFIG (3):
- ✅ ui_templates
- ✅ tenant_field_config
- ✅ tenant_field_configs

### COMPANY/USUARIOS (1):
- ✅ usuarios_usuarioempresa (EN ESPAÑOL - Debería ser company_users)

---

## 🚨 MAPEO: TABLAS EN BD vs MODELOS ESPERADOS

### HR - EMPLEADOS:
| Modelo Esperado | Tabla en BD | Estado | Notas |
|---|---|---|---|
| `Empleado` | `empleados` | ✅ EXISTE | **EN ESPAÑOL** |
| `Vacation` | `vacaciones` | ✅ EXISTE | **EN ESPAÑOL** |

### HR - NÓMINA:
| Modelo Esperado | Tabla en BD | Estado | Notas |
|---|---|---|---|
| `Payroll` | `nominas` | ✅ EXISTE | **EN ESPAÑOL** |
| `PayrollConcept` | `nomina_conceptos` | ✅ EXISTE | **EN ESPAÑOL** |
| `PayrollTemplate` | `nomina_plantillas` | ✅ EXISTE | **EN ESPAÑOL** |

### FINANZAS:
| Modelo Esperado | Tabla en BD | Estado | Notas |
|---|---|---|---|
| `CashMovement` | `caja_movimientos` | ✅ EXISTE | **EN ESPAÑOL** |
| `CashClosing` | `cierres_caja` | ✅ EXISTE | **EN ESPAÑOL** |

### CONTABILIDAD:
| Modelo Esperado | Tabla en BD | Estado | Notas |
|---|---|---|---|
| `ChartOfAccounts` | `plan_cuentas` | ✅ EXISTE | **EN ESPAÑOL** |
| `JournalEntry` | `asientos_contables` | ✅ EXISTE | **EN ESPAÑOL** |
| `JournalEntryLine` | `asiento_lineas` | ✅ EXISTE | **EN ESPAÑOL** |

### USUARIOS:
| Modelo Esperado | Tabla en BD | Estado | Notas |
|---|---|---|---|
| `CompanyUser` | `usuarios_usuarioempresa` | ✅ EXISTE | **EN ESPAÑOL** |

---

## 🎯 RECOMENDACIÓN

**Opción 1 (RECOMENDADA): Renombrar tablas en español a inglés**

Crear una nueva migración:
```sql
-- 2025-11-18_001_spanish_tables_to_english.sql
ALTER TABLE empleados RENAME TO employees;
ALTER TABLE vacaciones RENAME TO vacations;
ALTER TABLE nominas RENAME TO payrolls;
ALTER TABLE nomina_conceptos RENAME TO payroll_concepts;
ALTER TABLE nomina_plantillas RENAME TO payroll_templates;
ALTER TABLE caja_movimientos RENAME TO cash_movements;
ALTER TABLE cierres_caja RENAME TO cash_closings;
ALTER TABLE plan_cuentas RENAME TO chart_of_accounts;
ALTER TABLE asientos_contables RENAME TO journal_entries;
ALTER TABLE asiento_lineas RENAME TO journal_entry_lines;
ALTER TABLE usuarios_usuarioempresa RENAME TO company_users;
```

**Opción 2: Actualizar modelos SQLAlchemy para usar nombres españoles**

Modificar las clases del modelo para que apunten a tablas con nombre español:
```python
class Employee(Base):
    __tablename__ = "empleados"  # Nombre español en BD

class Payroll(Base):
    __tablename__ = "nominas"    # Nombre español en BD
```

---

## 🔗 REFERENCIAS

- Migraciones: `/ops/migrations/`
- Modelos: `/app/models/`
- Conflicto: Los modelos esperan nombres en inglés pero la BD tiene nombres en español
