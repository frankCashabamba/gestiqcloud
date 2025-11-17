# ⚡ QUICK REFERENCE - Cambios Realizados

**Última actualización:** 17 Nov 2025

---

## 📁 ARCHIVOS MODIFICADOS

### Migraciones en `/ops/migrations/`

**Actualizadas (5):**
```
✓ 2025-11-03_180_hr_empleados/up.sql
✓ 2025-11-03_180_hr_empleados/down.sql
✓ 2025-11-03_201_hr_nominas/up.sql
✓ 2025-11-03_201_hr_nominas/down.sql
✓ 2025-11-03_202_finance_caja/up.sql
✓ 2025-11-03_202_finance_caja/down.sql
✓ 2025-11-03_203_accounting/up.sql
✓ 2025-11-03_203_accounting/down.sql
✓ 2025-11-01_160_create_usuarios_usuarioempresa/up.sql
✓ 2025-11-01_160_create_usuarios_usuarioempresa/down.sql
```

**Creadas (10):**
```
✓ 2025-11-18_300_suppliers_system/up.sql
✓ 2025-11-18_300_suppliers_system/down.sql
✓ 2025-11-18_310_sales_system/up.sql
✓ 2025-11-18_310_sales_system/down.sql
✓ 2025-11-18_320_purchases_system/up.sql
✓ 2025-11-18_320_purchases_system/down.sql
✓ 2025-11-18_330_expenses_system/up.sql
✓ 2025-11-18_330_expenses_system/down.sql
✓ 2025-11-18_340_business_reference_tables/up.sql
✓ 2025-11-18_340_business_reference_tables/down.sql
✓ 2025-11-18_350_import_mappings_corrections/up.sql
✓ 2025-11-18_350_import_mappings_corrections/down.sql
```

## 📄 DOCUMENTOS GENERADOS

En `/` (raíz del proyecto):
```
✓ MIGRACIONES_ACTUALIZADAS.md          - Listado detallado de cambios
✓ CHECKLIST_ANTES_DE_BORRAR_BD.md      - Checklist de verificación
✓ RESUMEN_CAMBIOS_FINALES.md           - Resumen ejecutivo
✓ QUICK_REFERENCE.md                   - Este archivo
✓ VERIFICACION_FINAL_TABLAS.md         - Análisis original
✓ TABLAS_REALES_EN_BD.md               - Listado de tablas
✓ ANALISIS_TABLAS.md                   - Análisis original
```

---

## 🔄 RESUMEN DE CAMBIOS POR MIGRACIÓN

### 2025-11-03_180_hr_empleados
```
empleados           → employees
  usuario_id        → user_id
  codigo            → code
  nombre            → first_name
  apellidos         → last_name
  documento         → document_id
  fecha_nacimiento  → birth_date
  fecha_alta        → hire_date
  fecha_baja        → termination_date
  cargo             → position
  activo            → is_active

vacaciones          → vacations
  empleado_id       → employee_id
  fecha_inicio      → start_date
  fecha_fin         → end_date
  dias              → days
  estado            → status
  aprobado_por      → approved_by
  notas             → notes
```

### 2025-11-03_201_hr_nominas
```
nominas             → payrolls
  numero            → number
  empleado_id       → employee_id
  periodo_mes       → period_month
  periodo_ano       → period_year
  [Y 20+ columnas más]

nomina_conceptos    → payroll_concepts
nomina_plantillas   → payroll_templates

ENUM:
  nomina_status     → payroll_status
  nomina_tipo       → payroll_type
```

### 2025-11-03_202_finance_caja
```
caja_movimientos    → cash_movements
cierres_caja        → cash_closings
[20+ columnas renombradas]

ENUM:
  caja_movimiento_tipo      → cash_movement_type
  caja_movimiento_categoria → cash_movement_category
  cierre_caja_status        → cash_closing_status
```

### 2025-11-03_203_accounting
```
plan_cuentas        → chart_of_accounts
asientos_contables  → journal_entries
asiento_lineas      → journal_entry_lines
[25+ columnas renombradas]

ENUM:
  cuenta_tipo       → account_type
  asiento_status    → journal_entry_status
```

### 2025-11-01_160_create_usuarios_usuarioempresa
```
usuarios_usuarioempresa → company_users
[Constraints e índices renombrados]
```

---

## ➕ TABLAS NUEVAS

### 2025-11-18_300_suppliers_system
- `suppliers`
- `supplier_contacts`
- `supplier_addresses`

### 2025-11-18_310_sales_system
- `sales_orders`
- `sales_order_items`
- `sales`
- `deliveries`

### 2025-11-18_320_purchases_system
- `purchases`
- `purchase_lines`

### 2025-11-18_330_expenses_system
- `expenses`

### 2025-11-18_340_business_reference_tables
- `business_types`
- `business_categories`
- `company_categories`
- `business_hours`
- `user_profiles`
- `sector_templates`
- `sector_field_defaults`

### 2025-11-18_350_import_mappings_corrections
- `import_mappings`
- `import_item_corrections`

---

## 🎯 TABLA DE CONVERSIONES RÁPIDAS

| Español | English |
|---------|---------|
| empleados | employees |
| vacaciones | vacations |
| nominas | payrolls |
| nomina_conceptos | payroll_concepts |
| nomina_plantillas | payroll_templates |
| caja_movimientos | cash_movements |
| cierres_caja | cash_closings |
| plan_cuentas | chart_of_accounts |
| asientos_contables | journal_entries |
| asiento_lineas | journal_entry_lines |
| usuarios_usuarioempresa | company_users |

---

## 🔍 BÚSQUEDA RÁPIDA

**¿Dónde está la tabla X?**

| Tabla | Migración |
|-------|-----------|
| employees | 2025-11-03_180_hr_empleados |
| vacations | 2025-11-03_180_hr_empleados |
| payrolls | 2025-11-03_201_hr_nominas |
| payroll_concepts | 2025-11-03_201_hr_nominas |
| payroll_templates | 2025-11-03_201_hr_nominas |
| cash_movements | 2025-11-03_202_finance_caja |
| cash_closings | 2025-11-03_202_finance_caja |
| chart_of_accounts | 2025-11-03_203_accounting |
| journal_entries | 2025-11-03_203_accounting |
| journal_entry_lines | 2025-11-03_203_accounting |
| company_users | 2025-11-01_160_create_usuarios_usuarioempresa |
| suppliers | 2025-11-18_300_suppliers_system |
| supplier_contacts | 2025-11-18_300_suppliers_system |
| supplier_addresses | 2025-11-18_300_suppliers_system |
| sales_orders | 2025-11-18_310_sales_system |
| sales_order_items | 2025-11-18_310_sales_system |
| sales | 2025-11-18_310_sales_system |
| deliveries | 2025-11-18_310_sales_system |
| purchases | 2025-11-18_320_purchases_system |
| purchase_lines | 2025-11-18_320_purchases_system |
| expenses | 2025-11-18_330_expenses_system |
| business_types | 2025-11-18_340_business_reference_tables |
| user_profiles | 2025-11-18_340_business_reference_tables |
| sector_templates | 2025-11-18_340_business_reference_tables |

---

## ✅ VERIFICACIÓN RÁPIDA

```sql
-- ¿Cuántas tablas en INGLÉS?
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public';

-- ¿Quedan tablas en español?
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename ~ '[áéíóúñ]';
-- Esperado: (0 rows)

-- Listar todas
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

---

## 🚀 EJECUCIÓN RÁPIDA

**Paso 1: Backup**
```bash
pg_dump -U usuario -W tu_bd > backup_$(date +%Y%m%d).dump
```

**Paso 2: Borrar y crear**
```bash
dropdb -U usuario tu_bd
createdb -U usuario tu_bd
```

**Paso 3: Migraciones**
```bash
# Si usas Alembic
alembic upgrade head

# O SQL directo (39 archivos en orden)
for file in migrations/*/up.sql; do
    psql -U usuario -d tu_bd -f "$file"
done
```

---

## 📞 SOPORTE

Documentos de referencia completa:
- `MIGRACIONES_ACTUALIZADAS.md` - Cambios detallados
- `CHECKLIST_ANTES_DE_BORRAR_BD.md` - Verificaciones
- `RESUMEN_CAMBIOS_FINALES.md` - Resumen ejecutivo

Directorio de migraciones: `/ops/migrations/`
Directorio de modelos: `/app/models/`

---

**Estado:** ✅ COMPLETADO Y LISTO
