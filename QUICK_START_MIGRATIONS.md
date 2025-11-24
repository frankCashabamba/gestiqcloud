# ⚡ Quick Start: Migraciones Profesionales

## Resumen

Tienes un problema: **migraciones fragmentadas** en `ops/migrations/`.

Solución: **1 migración consolidada** que cree todas las tablas de una vez.

---

## 🚀 Plan de Acción

### 1️⃣ Generar Migración Consolidada

Ejecuta desde la raíz del proyecto:

```bash
# En PowerShell (Windows)
cd C:\Users\pc_cashabamba\Documents\GitHub\proyecto

# Generar migración
python scripts/generate_schema_sql.py --date 2025-11-21 --number 000
```

**Esto crea:**
```
ops/migrations/2025-11-21_000_complete_consolidated_schema/
├── up.sql      ← Aplicar migraciones
├── down.sql    ← Rollback
└── README.md   ← Documentación
```

### 2️⃣ Verificar Migración Generada

```bash
# Ver contenido (primeras líneas)
type ops\migrations\2025-11-21_000_complete_consolidated_schema\up.sql | Select-Object -First 100

# Ver tamaño
(Get-Item ops\migrations\2025-11-21_000_complete_consolidated_schema\up.sql).Length
```

### 3️⃣ Aplicar Migración

```bash
# Hacer backup primero (IMPORTANTE!)
docker exec db pg_dump -U postgres gestiqclouddb_dev > backup_$(date +%Y%m%d_%H%M%S).sql

# Aplicar migración
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-21_000_complete_consolidated_schema/up.sql

# Verificar tablas creadas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

### 4️⃣ Eliminar Migraciones Antiguas

```bash
# Mover a archivo
mkdir ops/migrations/_archive_consolidated
Move-Item ops/migrations/2025-11-* ops/migrations/_archive_consolidated/

# Quedará solo la nueva
# ops/migrations/2025-11-21_000_complete_consolidated_schema/
```

---

## 📊 Qué Sucede

### Antes (Actual)

```
ops/migrations/
├── 2025-11-01_000_baseline_modern/
├── 2025-11-02_231_product_categories_add_metadata/    ← Solo metadata
├── 2025-11-19_900_missing_tables/                      ← Tablas faltantes
├── 2025-11-19_905_add_stock_moves_tentative/          ← Un solo campo!
├── 2025-11-20_000_consolidated_final_schema/          ← ALTER con cambios dispersos
└── ... (40+ migraciones más)
```

❌ Problema: `business_types` está en 3+ migraciones

### Después (Profesional)

```
ops/migrations/
└── 2025-11-21_000_complete_consolidated_schema/
    ├── up.sql         ← Todas las tablas, definición completa
    ├── down.sql       ← Rollback limpio
    └── README.md      ← Documentación
```

✅ Profesional: 1 migración, todas las tablas correctas

---

## ⚙️ Requisitos

El script necesita que **en la raíz del proyecto** exista:

```
apps/backend/
├── app/
│   ├── config/
│   │   └── database.py   ← Define Base
│   ├── models/           ← Todos tus modelos
│   └── ...
├── requirements.txt      ← Dependencias
└── ...
```

Si hace falta instalar dependencias:

```bash
cd apps/backend
pip install -r requirements.txt
cd ../..
```

---

## ❌ Si el Script Falla

Si no funciona el script (por dependencias, etc.), **puedes hacerlo manual**:

### Opción A: Inspeccionar BD Actual

```bash
# Ver todas las tablas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"

# Ver estructura de tabla
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d business_types"
```

### Opción B: Crear Migración Manual

1. Usar `SHOW CREATE TABLE` en cada tabla existente
2. Consolidar en `up.sql`
3. Escribir `down.sql` (DROP TABLE en orden inverso)
4. Documentar en `README.md`

---

## 🔍 Verificación

Después de aplicar:

```bash
# Contar tablas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# Ver todas las tablas
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"

# Ver índices
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\di"
```

---

## ✅ Checklist

- [ ] Tengo backup de BD
- [ ] Generé migración: `python scripts/generate_schema_sql.py`
- [ ] Verifiqué contenido de `up.sql`
- [ ] Apliqué con `docker exec`
- [ ] Verifiqué tablas con `\dt`
- [ ] Eliminé migraciones antiguas

---

## 📚 Archivos de Referencia

- **Guía completa**: `GENERATE_MIGRATIONS.md`
- **Mapeo actual**: `MIGRACIONES_MODELOS.md`
- **Script**: `scripts/generate_schema_sql.py`

---

## 🎯 Beneficios

✅ **Limpio**: 1 migración en lugar de 40+
✅ **Profesional**: Índices y constraints correctos
✅ **Mantenible**: Fácil de entender
✅ **Idempotente**: Reutilizable
✅ **Documentado**: README automático

---

**¿Listo?**

```bash
cd C:\Users\pc_cashabamba\Documents\GitHub\proyecto
python scripts/generate_schema_sql.py --date 2025-11-21 --number 000
```
