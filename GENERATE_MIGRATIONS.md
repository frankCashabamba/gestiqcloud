# 🚀 Generar Migraciones Profesionales desde Modelos SQLAlchemy

## Problema Actual

Las migraciones en `ops/migrations/` están **fragmentadas**:
- ❌ Muchas migraciones pequeñas que alteran campos sueltos
- ❌ Mismas tablas modificadas en múltiples migraciones
- ❌ No profesional ni mantenible

## Solución

Crear **una migración consolidada** que defina todas las tablas **completas y correctas** desde los modelos SQLAlchemy.

---

## Opción 1: Script Automático (Recomendado)

### Uso

```bash
# 1. Desde la raíz del proyecto
cd C:\Users\pc_cashabamba\Documents\GitHub\proyecto

# 2. Ver preview del SQL (sin crear archivos)
python scripts/generate_schema_sql.py --output-only

# 3. Crear la migración
python scripts/generate_schema_sql.py --date 2025-11-21 --number 100

# 4. Esto crea: ops/migrations/2025-11-21_100_complete_consolidated_schema/
```

### Qué Genera

La migración contendrá:
- ✅ DROP de todas las tablas existentes (clean start)
- ✅ CREATE TABLE para todas las tablas en los modelos
- ✅ Indexes para rendimiento (40+ indexes)
- ✅ README.md con documentación

### Resultado

```
ops/migrations/
└── 2025-11-21_100_complete_consolidated_schema/
    ├── up.sql      (aplicar migración)
    ├── down.sql    (rollback)
    └── README.md   (documentación)
```

---

## Opción 2: Cleanup de Migraciones Actuales

Si quieres **limpiar** el historial:

```bash
# 1. Backup de migraciones actuales
mkdir ops/migrations/_archive_old
mv ops/migrations/2025-11-* ops/migrations/_archive_old/

# 2. Generar nueva migración consolidada
python scripts/generate_schema_sql.py --date 2025-11-21 --number 000

# 3. Aplicar
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-21_000_complete_consolidated_schema/up.sql

# 4. (Opcional) Eliminar archivo antiguo
rm -rf ops/migrations/_archive_old/
```

---

## Opción 3: Manual (Si algo falla)

### Paso 1: Ver qué tablas existen

```bash
python scripts/generate_schema_sql.py --output-only | head -200
```

### Paso 2: Crear migración manualmente

1. Copiar contenido SQL del script
2. Crear carpeta: `ops/migrations/2025-11-21_100_description/`
3. Crear archivos:
   - `up.sql` - SQL del script
   - `down.sql` - Rollback
   - `README.md` - Documentación

---

## 🔥 Flujo Completo (Sin Datos)

Dado que **no tienes datos**, puedes hacer:

```bash
# 1. Eliminar base de datos actual (CUIDADO!)
docker exec db psql -U postgres -c "DROP DATABASE gestiqclouddb_dev;"

# 2. Crear base de datos nueva
docker exec db psql -U postgres -c "CREATE DATABASE gestiqclouddb_dev;"

# 3. Generar migración consolidada
python scripts/generate_schema_sql.py --date 2025-11-21 --number 000

# 4. Aplicar migración
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-21_000_complete_consolidated_schema/up.sql

# 5. Verificar tablas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

---

## ⚠️ Requisitos Previos

El script necesita:
- ✅ Python 3.8+
- ✅ SQLAlchemy y dependencias del backend
- ✅ Estar en la raíz del proyecto

### Instalar Dependencias (si es necesario)

```bash
cd apps/backend
pip install -r requirements.txt
```

---

## 📊 Qué Se Genera

### up.sql Incluye:
1. **DROP de tablas existentes** (clean start)
   - Orden inverso para respetar FKs
   - Usa CASCADE para eliminar dependencias

2. **CREATE TABLE** para ~50 tablas
   - Definición completa de columnas
   - Tipos de datos correctos (UUID, JSONB, etc.)
   - Constraints (NOT NULL, UNIQUE, FK)

3. **Indexes** (~40 índices)
   - `idx_<table>_tenant_id` - Multi-tenancy
   - `idx_<table>_<fk>` - Join optimization
   - `idx_<table>_<search>` - Search fields (name, sku)
   - `idx_<table>_created_at` - Audit queries

### down.sql Incluye:
- DROP de todas las tablas (rollback completo)

### README.md Incluye:
- Descripción de cambios
- Lista completa de tablas
- Instrucciones de aplicación
- Documentación de indexes

---

## 🎯 Después de Aplicar

```bash
# 1. Verificar tablas creadas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"

# 2. Verificar índices
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\di"

# 3. Verificar estructura de tabla específica
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d products"
```

---

## 🚨 Si Algo Sale Mal

### Rollback

```bash
# Usar down.sql
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-21_100_complete_consolidated_schema/down.sql
```

### Restaurar desde backup

```bash
# Si hiciste backup antes
docker exec -i db psql -U postgres gestiqclouddb_dev < backup_before_migration.sql
```

---

## 📝 Convención de Nombres

```
YYYY-MM-DD_NNN_description/
├── up.sql
├── down.sql
└── README.md
```

- `2025-11-21` - Fecha
- `100` - Número secuencial
- `complete_consolidated_schema` - Descripción

---

## ✅ Checklist

- [ ] Tengo backup de la BD
- [ ] He ejecutado `python scripts/generate_schema_sql.py --output-only`
- [ ] He revisado el SQL en el preview
- [ ] He ejecutado `python scripts/generate_schema_sql.py --date 2025-11-21 --number 000`
- [ ] He revisado archivos generados en `ops/migrations/`
- [ ] He aplicado la migración con `docker exec`
- [ ] He verificado tablas con `\dt`

---

## Ventajas de Este Enfoque

✅ **Limpio**: Una migración, todas las tablas
✅ **Profesional**: Índices y constraints correctos
✅ **Mantenible**: Fácil de entender qué define cada tabla
✅ **Idempotente**: Usa `IF NOT EXISTS` / `CASCADE`
✅ **Documentado**: README automático
✅ **Reversible**: down.sql funcional

---

**Listo para comenzar?**

```bash
python scripts/generate_schema_sql.py --date 2025-11-21 --number 000
```
