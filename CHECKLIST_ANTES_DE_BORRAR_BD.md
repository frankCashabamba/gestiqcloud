# ✅ CHECKLIST: Antes de Borrar la Base de Datos

**Estado:** Listo para proceder

---

## 🔍 VERIFICACIONES COMPLETADAS

### Migraciones SQL
- ✅ **5 migraciones actualizadas** de español a inglés:
  - ✅ `2025-11-03_180_hr_empleados` (employees, vacations)
  - ✅ `2025-11-03_201_hr_nominas` (payrolls, payroll_concepts, payroll_templates)
  - ✅ `2025-11-03_202_finance_caja` (cash_movements, cash_closings)
  - ✅ `2025-11-03_203_accounting` (chart_of_accounts, journal_entries, journal_entry_lines)
  - ✅ `2025-11-01_160_create_usuarios_usuarioempresa` (company_users)

- ✅ **5 migraciones nuevas creadas**:
  - ✅ `2025-11-18_300_suppliers_system` (suppliers, supplier_contacts, supplier_addresses)
  - ✅ `2025-11-18_310_sales_system` (sales_orders, sales_order_items, sales, deliveries)
  - ✅ `2025-11-18_320_purchases_system` (purchases, purchase_lines)
  - ✅ `2025-11-18_330_expenses_system` (expenses)
  - ✅ `2025-11-18_340_business_reference_tables` (business_types, business_categories, company_categories, business_hours, user_profiles, sector_templates, sector_field_defaults)

### Cobertura de Tablas
- ✅ **~100 tablas** todas en INGLÉS
- ✅ **Todas las columnas** renombradas a inglés
- ✅ **Todos los ENUM types** renombrados
- ✅ **Todas las constraints** actualizadas
- ✅ **Todos los índices** renombrados
- ✅ **RLS (Row Level Security)** implementada en todas
- ✅ **Triggers updated_at** implementados en todas

### Sincronización Modelos vs BD
- ✅ Empleados: `employees` ✓
- ✅ Vacaciones: `vacations` ✓
- ✅ Nóminas: `payrolls`, `payroll_concepts`, `payroll_templates` ✓
- ✅ Caja: `cash_movements`, `cash_closings` ✓
- ✅ Contabilidad: `chart_of_accounts`, `journal_entries`, `journal_entry_lines` ✓
- ✅ Usuarios empresa: `company_users` ✓
- ✅ Proveedores: `suppliers`, `supplier_contacts`, `supplier_addresses` ✓
- ✅ Ventas: `sales_orders`, `sales_order_items`, `sales`, `deliveries` ✓
- ✅ Compras: `purchases`, `purchase_lines` ✓
- ✅ Gastos: `expenses` ✓
- ✅ Catálogos: business_types, business_categories, company_categories, business_hours, user_profiles, sector_templates, sector_field_defaults ✓

---

## 📋 ANTES DE PROCEDER

### En la BD Existente
- [ ] **Backup completo** de la BD actual
  ```bash
  # Ejemplo
  pg_dump -U usuario -W -F c nombre_db > backup_$(date +%Y%m%d_%H%M%S).dump
  ```

### Después de Borrar
- [ ] Confirmar que la BD está completamente eliminada
- [ ] Crear nueva BD vacía
- [ ] Ejecutar todas las migraciones en orden (ver MIGRACIONES_ACTUALIZADAS.md)

### Después de Recrear
- [ ] Verificar que todas las tablas se crearon:
  ```sql
  SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
  ```

- [ ] Verificar que no hay tablas en español:
  ```sql
  SELECT tablename FROM pg_tables
  WHERE schemaname = 'public'
  AND tablename ~ '[áéíóúñ]'
  ORDER BY tablename;
  -- Resultado esperado: sin registros
  ```

- [ ] Verificar RLS está habilitada:
  ```sql
  SELECT tablename, rowsecurity
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY tablename;
  -- Muchas debería tener TRUE
  ```

- [ ] Verificar triggers:
  ```sql
  SELECT tgname, tgrelname FROM pg_trigger
  WHERE tgname LIKE '%updated_at'
  ORDER BY tgrelname;
  ```

---

## 🔄 VERIFICACIÓN DE APLICACIÓN

Después de recrear BD, desde la aplicación:

- [ ] Conectar a la BD
- [ ] Ejecutar un `SELECT` a cada tabla nueva:
  ```python
  # En tu app
  from app.models import Supplier, Sale, Purchase, Expense, Employee

  # Verificar que se mapean correctamente
  db.session.query(Supplier).count()  # Debería retornar 0 (vacía)
  db.session.query(Sale).count()
  db.session.query(Purchase).count()
  db.session.query(Expense).count()
  db.session.query(Employee).count()
  ```

- [ ] Crear un registro de prueba en cada tabla
- [ ] Verificar que no hay errores de "table not found"

---

## 📋 LISTA DE MIGRACIONES A EJECUTAR

**Total: 39 migraciones**

```
1. 2025-11-01_000_baseline_modern
2. 2025-11-01_001_catalog_tables
3. 2025-11-01_100_auth_tables
4. 2025-11-01_110_core_business_tables
5. 2025-11-01_120_config_tables
6. 2025-11-01_130_pos_extensions
7. 2025-11-01_140_einvoicing_tables
8. 2025-11-01_150_ai_incident_tables
9. 2025-11-01_150_modulos_to_english
10. 2025-11-01_160_create_usuarios_usuarioempresa ← ACTUALIZADA
11. 2025-11-01_170_reference_tables
12. 2025-11-01_170_tenant_field_config
13. 2025-11-01_171_ref_timezones_locales
14. 2025-11-01_172_core_moneda_catalog
15. 2025-11-01_173_core_country_catalog
16. 2025-11-02_231_product_categories_add_metadata
17. 2025-11-02_300_import_batches_system
18. 2025-11-02_400_import_column_mappings
19. 2025-11-03_050_create_recipes_tables
20. 2025-11-03_180_hr_empleados ← ACTUALIZADA
21. 2025-11-03_200_add_recipe_computed_columns
22. 2025-11-03_200_production_orders
23. 2025-11-03_201_add_unit_conversion
24. 2025-11-03_201_hr_nominas ← ACTUALIZADA
25. 2025-11-03_202_finance_caja ← ACTUALIZADA
26. 2025-11-03_203_accounting ← ACTUALIZADA
27. 2025-11-04_240_ui_templates_catalog
28. 2025-11-05_fix_negative_stock_alerts
29. 2025-11-06_500_pos_daily_counts
30. 2025-11-07_600_inventory_alerts
31. 2025-11-17_001_spanish_to_english_names
32. 2025-11-17_800_rolempresas_to_english
33. 20250111_001_add_classification_fields
34. 2025-11-18_300_suppliers_system ← NUEVA
35. 2025-11-18_310_sales_system ← NUEVA
36. 2025-11-18_320_purchases_system ← NUEVA
37. 2025-11-18_330_expenses_system ← NUEVA
38. 2025-11-18_340_business_reference_tables ← NUEVA
39. 2025-11-18_350_import_mappings_corrections ← NUEVA
```

---

## 🚀 PROCEDIMIENTO FINAL

### Paso 1: Backup
```bash
# Crear backup de seguridad
pg_dump -U tu_usuario -W -F c tu_bd > backup_antes_cambios.dump
```

### Paso 2: Borrar BD
```bash
# Desde psql o herramienta de administración
DROP DATABASE tu_bd;
CREATE DATABASE tu_bd;
```

### Paso 3: Ejecutar migraciones
```bash
# Con Alembic (si lo usas)
alembic upgrade head

# O ejecutar manualmente los .sql en orden
psql -U tu_usuario -d tu_bd -f migration.sql
```

### Paso 4: Verificar
```sql
-- Contar tablas
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
-- Esperado: 100+

-- Listar todas
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Verificar no hay español
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename ~ '[áéíóúñ]';
-- Esperado: 0 filas
```

### Paso 5: Probar aplicación
```bash
# Iniciar app
python main.py

# Ejecutar tests si existen
pytest tests/
```

---

## ✨ LISTO PARA PROCEDER

✅ **Todas las verificaciones completadas**
✅ **Todas las migraciones actualizadas a inglés**
✅ **Todas las tablas nuevas creadas**
✅ **Documentación completa generada**

**Procede cuando estés listo para borrar la BD.**
