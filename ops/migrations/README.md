# Migraciones de Base de Datos

## 📁 Estructura

```
ops/migrations/
├── 2025-11-01_000_baseline_modern/   # ✅ BASELINE ACTIVA
│   ├── up.sql
│   ├── down.sql
│   └── README.md
└── _archive/                          # 📦 Historial (39 migraciones)
    ├── 2025-01-20_125_warehouses/
    ├── 2025-10-26_000_baseline/
    ├── ...
    └── 2025-11-01_250_fresh_start_english/
```

## 🎯 Migración Activa

### 2025-11-01_000_baseline_modern
**Estado**: ✅ Aplicada  
**Versión**: 2.0.0  
**Descripción**: Baseline consolidada con schema moderno 100% inglés

Esta migración crea el esquema completo desde cero:
- Core: `tenants`, `product_categories`
- Catalog: `products`
- Inventory: `warehouses`, `stock_items`, `stock_moves`, `stock_alerts`
- POS: `pos_registers`, `pos_shifts`, `pos_receipts`, `pos_receipt_lines`, `pos_payments`

**Ver**: [2025-11-01_000_baseline_modern/README.md](./2025-11-01_000_baseline_modern/README.md)

## 📜 Historial

Las 39 migraciones anteriores (Oct-Nov 2025) están archivadas en `_archive/`:
- Limpieza legacy → moderno
- Migración a UUIDs
- Renombrado español → inglés
- Fresh start final

**Ver**: [_archive/README.md](./_archive/README.md)

## 🚀 Aplicar Migraciones

### Baseline (Fresh Install)

```bash
# 1. Asegurar que auth_user y modulos_* existen
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt" | grep auth_user

# 2. Aplicar baseline
docker exec -i db psql -U postgres -d gestiqclouddb_dev < \
  ops/migrations/2025-11-01_000_baseline_modern/up.sql

# 3. Verificar tablas creadas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

### Nueva Migración (Futura)

```bash
# 1. Crear carpeta (siguiente número disponible)
mkdir ops/migrations/2025-11-XX_001_description

# 2. Crear archivos
touch ops/migrations/2025-11-XX_001_description/up.sql
touch ops/migrations/2025-11-XX_001_description/down.sql
touch ops/migrations/2025-11-XX_001_description/README.md

# 3. Escribir SQL
vim ops/migrations/2025-11-XX_001_description/up.sql

# 4. Aplicar
docker exec -i db psql -U postgres -d gestiqclouddb_dev < \
  ops/migrations/2025-11-XX_001_description/up.sql
```

## 📝 Convenciones

### Nomenclatura
```
YYYY-MM-DD_NNN_description/
```

- **YYYY-MM-DD**: Fecha de creación
- **NNN**: Número secuencial (001, 002, ...)
- **description**: Descripción corta en inglés (snake_case)

### Archivos Requeridos

1. **up.sql**: Migración forward
   ```sql
   BEGIN;
   -- Cambios aquí
   COMMIT;
   ```

2. **down.sql**: Rollback
   ```sql
   BEGIN;
   -- Revertir cambios
   COMMIT;
   ```

3. **README.md**: Documentación
   - Descripción
   - Cambios
   - Prerequisitos
   - Comandos

### Buenas Prácticas

✅ **DO**:
- Usar transacciones (`BEGIN`...`COMMIT`)
- Usar `IF NOT EXISTS` / `IF EXISTS`
- Documentar cambios en README
- Probar rollback antes de aplicar
- Usar nombres en inglés
- Incluir índices necesarios

❌ **DON'T**:
- No hacer cambios destructivos sin backup
- No mezclar cambios de schema y datos
- No usar nombres en español
- No olvidar el down.sql

## 🔄 Rollback

### Última Migración
```bash
# Si aplicaste una migración incorrecta
docker exec -i db psql -U postgres -d gestiqclouddb_dev < \
  ops/migrations/2025-11-XX_NNN_description/down.sql
```

### Baseline Completo (⚠️ PELIGROSO)
```bash
# Esto elimina TODAS las tablas (excepto auth_user y modulos_*)
docker exec -i db psql -U postgres -d gestiqclouddb_dev < \
  ops/migrations/2025-11-01_000_baseline_modern/down.sql
```

## 📊 Estado Actual

| Migración | Aplicada | Fecha | Notas |
|-----------|----------|-------|-------|
| 2025-11-01_000_baseline_modern | ✅ | 2025-11-01 | Schema v2.0 |

## 🗄️ Backup Antes de Migrar

```bash
# Siempre hacer backup antes de migración
docker exec db pg_dump -U postgres gestiqclouddb_dev > \
  backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# Restaurar si algo sale mal
docker exec -i db psql -U postgres gestiqclouddb_dev < backup_before_migration_*.sql
```

## 🔍 Verificación

### Schema
```bash
# Ver todas las tablas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"

# Ver estructura de tabla específica
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d products"

# Ver índices
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\di"
```

### Datos
```bash
# Contar registros
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT count(*) FROM products;"

# Verificar RLS
docker exec db psql -U postgres -d gestiqclouddb_dev -c "
  SELECT tablename, policyname 
  FROM pg_policies 
  WHERE tablename = 'products';
"
```

## 📚 Referencias

- **Baseline actual**: [2025-11-01_000_baseline_modern/README.md](./2025-11-01_000_baseline_modern/README.md)
- **Archivo histórico**: [_archive/README.md](./_archive/README.md)
- **Schema moderno**: Ver `/README_DB.md`
- **Guía desarrollo**: Ver `/README_DEV.md`

---

**Última actualización**: Nov 2025  
**Versión baseline**: 2.0.0  
**Próxima migración**: 2025-11-XX_001_*
