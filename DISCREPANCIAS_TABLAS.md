# ⚠️ DISCREPANCIAS CRÍTICAS: Nombres de Tablas en BD vs Modelos

**Estado:** CONFLICTO ENCONTRADO - Las migraciones crean tablas en ESPAÑOL pero los modelos las esperan en INGLÉS

---

## 🔴 TABLAS CON NOMBRE DIFERENTE EN BD vs MODELOS

| Modelo Espera | Tabla Actual en BD | Problema | Migración |
|---|---|---|---|
| `cash_movements` | `caja_movimientos` | ❌ MISMATCH | 2025-11-03_202_finance_caja |
| `cash_closings` | `cierres_caja` | ❌ MISMATCH | 2025-11-03_202_finance_caja |
| `employees` | `empleados` | ❌ MISMATCH | 2025-11-03_180_hr_empleados |
| `vacations` | `vacaciones` | ❌ MISMATCH | 2025-11-03_180_hr_empleados |
| `payrolls` | `nominas` | ❌ MISMATCH | 2025-11-03_201_hr_nominas |
| `payroll_concepts` | `nomina_conceptos` | ❌ MISMATCH | 2025-11-03_201_hr_nominas |
| `payroll_templates` | `nomina_plantillas` | ❌ MISMATCH | 2025-11-03_201_hr_nominas |
| `chart_of_accounts` | `plan_cuentas` | ❌ MISMATCH | 2025-11-03_203_accounting |
| `journal_entries` | `asientos_contables` | ❌ MISMATCH | 2025-11-03_203_accounting |
| `journal_entry_lines` | `asiento_lineas` | ❌ MISMATCH | 2025-11-03_203_accounting |
| `company_users` | `usuarios_usuarioempresa` | ❌ MISMATCH | 2025-11-01_160_create_usuarios_usuarioempresa |

---

## 🎯 SOLUCIÓN RECOMENDADA (ANTES de borrar BD)

**Crear una migración de "corrección" que renombre las tablas en español a inglés:**

### Archivo: `ops/migrations/2025-11-18_001_spanish_to_english_final/up.sql`

```sql
-- =====================================================
-- MIGRACIÓN: Renombrar todas las tablas de español a inglés
-- =====================================================

BEGIN;

-- HR EMPLEADOS
ALTER TABLE IF EXISTS empleados RENAME TO employees;
ALTER TABLE IF EXISTS vacaciones RENAME TO vacations;

-- HR NÓMINAS
ALTER TABLE IF EXISTS nominas RENAME TO payrolls;
ALTER TABLE IF EXISTS nomina_conceptos RENAME TO payroll_concepts;
ALTER TABLE IF EXISTS nomina_plantillas RENAME TO payroll_templates;

-- FINANZAS CAJA
ALTER TABLE IF EXISTS caja_movimientos RENAME TO cash_movements;
ALTER TABLE IF EXISTS cierres_caja RENAME TO cash_closings;

-- CONTABILIDAD
ALTER TABLE IF EXISTS plan_cuentas RENAME TO chart_of_accounts;
ALTER TABLE IF EXISTS asientos_contables RENAME TO journal_entries;
ALTER TABLE IF EXISTS asiento_lineas RENAME TO journal_entry_lines;

-- USUARIOS/EMPRESA
ALTER TABLE IF EXISTS usuarios_usuarioempresa RENAME TO company_users;

COMMIT;
```

### Archivo: `ops/migrations/2025-11-18_001_spanish_to_english_final/down.sql`

```sql
-- =====================================================
-- ROLLBACK: Revertir renombres de español a inglés
-- =====================================================

BEGIN;

-- USUARIOS/EMPRESA
ALTER TABLE IF EXISTS company_users RENAME TO usuarios_usuarioempresa;

-- CONTABILIDAD
ALTER TABLE IF EXISTS journal_entry_lines RENAME TO asiento_lineas;
ALTER TABLE IF EXISTS journal_entries RENAME TO asientos_contables;
ALTER TABLE IF EXISTS chart_of_accounts RENAME TO plan_cuentas;

-- FINANZAS CAJA
ALTER TABLE IF EXISTS cash_closings RENAME TO cierres_caja;
ALTER TABLE IF EXISTS cash_movements RENAME TO caja_movimientos;

-- HR NÓMINAS
ALTER TABLE IF EXISTS payroll_templates RENAME TO nomina_plantillas;
ALTER TABLE IF EXISTS payroll_concepts RENAME TO nomina_conceptos;
ALTER TABLE IF EXISTS payrolls RENAME TO nominas;

-- HR EMPLEADOS
ALTER TABLE IF EXISTS vacations RENAME TO vacaciones;
ALTER TABLE IF EXISTS employees RENAME TO empleados;

COMMIT;
```

---

## 📋 VERIFICACIÓN DE DEPENDENCIAS

Estas tablas tienen FOREIGN KEYS que apuntan a las tablas en español. Necesitarás:

### EN `caja_movimientos`:
- Foreign Key a `tenants(id)` ✅ Ya en inglés
- Foreign Key a `usuarios_usuarioempresa` (→ `company_users`)

### EN `empleados`:
- Foreign Key a `tenants(id)` ✅ Ya en inglés
- Foreign Key a `usuarios` (probablemente auth_user)

### EN `vacaciones`:
- Foreign Key a `empleados` → `employees`
- Foreign Key a `tenants(id)` ✅ Ya en inglés

### EN `nominas`:
- Foreign Key a `empleados` → `employees`
- Foreign Key a `tenants(id)` ✅ Ya en inglés

### EN `plan_cuentas`:
- Foreign Key a `tenants(id)` ✅ Ya en inglés
- Self-referencing: `padre_id` → `plan_cuentas.id` → `chart_of_accounts.id`

### EN `asientos_contables`:
- Foreign Key a `tenants(id)` ✅ Ya en inglés
- Foreign Key a `plan_cuentas` → `chart_of_accounts`

### EN `asiento_lineas`:
- Foreign Key a `asientos_contables` → `journal_entries`
- Foreign Key a `plan_cuentas` → `chart_of_accounts`

---

## 🔧 PASOS A SEGUIR

### Opción A: Ejecutar la migración de rename (RECOMENDADO)

1. Crear la migración en `ops/migrations/2025-11-18_001_spanish_to_english_final/`
2. Ejecutar antes de borrar la BD
3. Después de borrar y recrear, las tablas estarán con nombres correctos

### Opción B: Modificar los modelos para apuntar a tablas en español

Si prefieres mantener los nombres en español en la BD:

```python
# app/models/finance/caja.py
class CashMovement(Base):
    __tablename__ = "caja_movimientos"  # Cambiar a español

class CashClosing(Base):
    __tablename__ = "cierres_caja"  # Cambiar a español

# app/models/hr/empleado.py
class Empleado(Base):
    __tablename__ = "empleados"  # Cambiar a español

class Vacacion(Base):
    __tablename__ = "vacaciones"  # Cambiar a español

# Y así para todas...
```

---

## 📝 RESUMEN

**Situación actual:**
- 11 tablas con nombres en ESPAÑOL en la BD
- Modelos de SQLAlchemy esperan nombres en INGLÉS
- Esto causará `OperationalError: table "cash_movements" does not exist`

**Solución:**
- Ejecutar migración de rename antes de empezar con la BD nueva
- O actualizar todos los `__tablename__` en los modelos
