# 📊 Resumen de Migración: Español → Inglés

## Estado Actual ⚠️

**La infraestructura de migraciones está **parcialmente completada**. Faltan ~10-15 tablas.**

| Componente | Estado | Detalles |
|-----------|--------|---------|
| Scripts SQL Base | ⚠️ | 28 migraciones existentes + 5 por crear |
| Auth Tables | ✅ | `2025-11-01_100_auth_tables` creada |
| Tablas Críticas | ❌ | clients, invoices, invoice_lines FALTA |
| Renombre Tablas | ✅ | `2025-11-17_001_spanish_to_english_names` completada |
| Renombre Columnas | ✅ | Expenses, Bank, Payroll, Suppliers, etc. |
| Scripts Python | ✅ | `ops/scripts/migrate_all_migrations.py` disponible |
| Modelos ORM | ✅ | Ya en inglés en `/app/models/` |
| Documentación | ✅ | Plans, status, y missing migrations documentados |

---

## ⚠️ Tablas Que Faltan (Críticas)

**Necesarias ANTES de ejecutar migraciones completas:**

- ❌ `clients` - Base para ventas (CRÍTICA)
- ❌ `invoices` - Facturas (CRÍTICA)
- ❌ `invoice_lines` - Líneas de facturas (CRÍTICA)
- ❌ `doc_series` - Numeración de documentos
- ❌ `base_roles` - Roles globales
- ❌ `store_credits` - Crédito de tienda (POS)
- ❌ `store_credit_events` - Eventos de crédito
- ❌ `einv_credentials` - E-invoicing
- ❌ `incidents` - Reportes/alertas
- ❌ `notification_channels` - Canales de notificación

**Ver:** `ops/MISSING_MIGRATIONS.md` para detalles completos

---

## 🚀 Antes de Ejecutar

```bash
# Opción 1: Comando directo (recomendado)
python ops/scripts/migrate_all_migrations.py --database-url "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"

# Opción 2: Con variable de entorno
export DATABASE_URL="postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
python ops/scripts/migrate_all_migrations.py

# Opción 3: Dry run (ver sin ejecutar)
python ops/scripts/migrate_all_migrations.py --database-url "..." --dry-run
```

---

## 📋 Qué Se Migra

### Tablas Principales Renombradas (23 tablas)

**Proveedores:**
- `proveedores` → `suppliers`
- `proveedor_contactos` → `supplier_contacts`
- `proveedor_direcciones` → `supplier_addresses`

**Compras:**
- `compras` → `purchases`
- `compra_lineas` → `purchase_lines`

**Ventas:**
- `ventas` → `sales`

**Gastos:**
- `gastos` → `expenses`

**Finanzas:**
- `banco_movimientos` → `bank_movements`

**RR.HH:**
- `nominas` → `payrolls`
- `nomina_conceptos` → `payroll_items`
- `nomina_plantillas` → `payroll_templates`

**Módulos:**
- `modulos_modulo` → `modules`
- `modulos_empresamodulo` → `company_modules`
- `modulos_moduloasignado` → `assigned_modules`

**Configuración de Empresa:**
- `core_rolempresa` → `company_roles`
- `core_tipoempresa` → `company_types`
- `core_tiponegocio` → `business_types`
- `core_configuracionempresa` → `company_settings`
- `core_configuracioninventarioempresa` → `company_inventory_settings`
- `usuarios_usuarioempresa` → `user_companies`
- `usuarios_usuariorolempresa` → `user_company_roles`

**Otros:**
- `auditoria_importacion` → `import_audit`
- `lineas_panaderia` → `bakery_lines`
- `lineas_taller` → `workshop_lines`
- `facturas_temp` → `invoices_temp`
- `core_moneda` → `currencies_legacy`

### Columnas Renombradas (100+)

**Ejemplos comunes:**
- `codigo` → `code`
- `nombre` → `name`
- `nombre_comercial` → `trade_name`
- `telefono` → `phone`
- `email` → `email`
- `web` → `website`
- `activo` → `is_active`
- `fecha` → `date`
- `estado` → `status`
- `numero` → `number`
- `proveedor_id` → `supplier_id`
- `cliente_id` → `customer_id`
- `subtotal` → `subtotal`
- `impuestos` → `taxes`
- `total` → `total`

---

## ✨ Características de los Scripts

✅ **Idempotentes** - Se pueden ejecutar múltiples veces sin problemas
✅ **Transaccionales** - Usan `BEGIN/COMMIT` para integridad
✅ **Validadas** - IF EXISTS en todas las tablas
✅ **Documentadas** - Comentarios explicativos
✅ **Reversibles** - Archivos `down.sql` disponibles

---

## 📝 Después de Ejecutar

### 1. Validar Base de Datos
```bash
# Conectar a PostgreSQL
psql -h localhost -d gestiqclouddb_dev -U postgres

# Listar todas las tablas
\dt

# Ver estructura de una tabla
\d suppliers

# Contar registros
SELECT COUNT(*) FROM suppliers;
SELECT COUNT(*) FROM purchases;
```

### 2. Actualizar Código Python

Buscar y actualizar referencias:
```bash
# En /app/schemas/ - cambiar nombres de campos
# En /app/services/ - actualizar queries SQL
# En /app/routers/ - actualizar referencias a tablas

# Búsqueda útil:
grep -r "proveedores" app/
grep -r "compras" app/
grep -r "gastos" app/
```

### 3. Ejecutar Tests
```bash
pytest tests/ -v
```

### 4. Validar Integridad
```bash
# Revisar foreign keys
SELECT constraint_name, table_name FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY';

# Revisar índices
\di

# Revisar vistas (si existen)
\dv
```

---

## 📂 Ubicación de Archivos

```
proyecto/
├── ops/
│   ├── migrations/
│   │   ├── 2025-11-01_000_baseline_modern/up.sql
│   │   ├── 2025-11-17_001_spanish_to_english_names/up.sql ← MAIN
│   │   ├── 2025-11-17_800_rolempresas_to_english/up.sql ← ROLE RENAME
│   │   └── [otros scripts]
│   └── scripts/
│       └── migrate_all_migrations.py ← EJECUTAR ESTE
├── NAMING_MIGRATION_PLAN.md
├── MIGRATION_SUMMARY.md (este archivo)
└── ops/MIGRATION_STATUS.md (detalles completos)
```

---

## 🔍 Validación Post-Migración

Script de validación SQL disponible en:
```
ops/migrations/validate_migration.sql
```

Ejecutar con:
```bash
psql -h localhost -d gestiqclouddb_dev -U postgres -f ops/migrations/validate_migration.sql
```

---

## ⚠️ Consideraciones Importantes

- **Backup**: Hacer backup ANTES de ejecutar
- **Producción**: Probar en entorno de desarrollo primero
- **Permisos**: El usuario PostgreSQL necesita permisos DDL
- **Foreign Keys**: Se actualizan automáticamente en las migraciones
- **Índices**: Se mantienen y renombran

---

## 🆘 En Caso de Problemas

### Error: "table already exists"
→ Las migraciones ya se ejecutaron. Verificar con `\dt`

### Error: "column does not exist"
→ Columnas aún están en español. Ejecutar migraciones de renombre.

### Error: "permission denied"
→ El usuario PostgreSQL no tiene permisos DDL. Usar rol superuser.

### Rollback
```bash
psql -h localhost -d gestiqclouddb_dev -f 2025-11-17_001_spanish_to_english_names/down.sql
```

---

## 📞 Contacto / Soporte

Revisar documentación en:
- `NAMING_MIGRATION_PLAN.md` - Detalles de cambios
- `ops/MIGRATION_STATUS.md` - Estado completo
- `ops/migrations/validate_migration.sql` - Validación

---

**Última actualización:** 17 Nov 2025
**Versión:** 1.0
**Estado:** ✅ LISTO PARA EJECUTAR
