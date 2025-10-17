# Quick Start - Tenant Migration Imports

Guía rápida para aplicar la migración de tenantización del módulo de imports.

## ⚡ TL;DR

```bash
# 1. Backup
pg_dump $DATABASE_URL > backup.sql

# 2. Aplicar
python ops/scripts/apply_tenant_migration_imports.py

# 3. Verificar
python ops/scripts/verify_tenant_migration_imports.py
```

---

## 📋 Pre-requisitos (Verificar ANTES)

```bash
# PostgreSQL 12+
psql $DATABASE_URL -c "SELECT version();"

# Tabla tenants existe
psql $DATABASE_URL -c "SELECT COUNT(*) FROM public.tenants;"

# core_empresa tiene tenant_id
psql $DATABASE_URL -c "SELECT COUNT(*) FROM core_empresa WHERE tenant_id IS NULL;"
# Debe retornar 0

# import_batches tiene tenant_id (migración 2025-10-09_016)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM import_batches WHERE tenant_id IS NULL;"
# Debe retornar 0
```

---

## 🚀 Pasos de Aplicación

### 1. Backup (OBLIGATORIO)

```bash
# Backup completo
pg_dump $DATABASE_URL -Fc > backup_imports_$(date +%Y%m%d_%H%M%S).pgcustom

# O backup de solo tablas imports
pg_dump $DATABASE_URL -Fc -t 'import_*' > backup_imports_tables.pgcustom
```

### 2. Dry Run (Revisar SQL)

```bash
python ops/scripts/apply_tenant_migration_imports.py --dry-run | less
```

**Verificar**:
- ✅ Comandos `ALTER TABLE ADD COLUMN tenant_id`
- ✅ Comandos `UPDATE ... SET tenant_id`
- ✅ Comandos `ALTER COLUMN TYPE jsonb`
- ✅ Comandos `CREATE INDEX`

### 3. Aplicar Migración

```bash
# Con logging
python ops/scripts/apply_tenant_migration_imports.py 2>&1 | tee migration.log

# Duración esperada: 1-5 minutos (depende del volumen de datos)
```

**Output esperado**:
```
Connecting to database...
============================================================
Migration: Add tenant_id to imports module
SQL File: up.sql
============================================================

Validating prerequisites...
Executing statement 1/45...
Executing statement 2/45...
...
Executing statement 45/45...
✅ Migration applied successfully!

Next steps:
  - Update application code to use tenant_id
  - Test RLS policies with: python ops/scripts/test_rls.py
  - empresa_id will be deprecated in v2.0
```

### 4. Verificar

```bash
python ops/scripts/verify_tenant_migration_imports.py
```

**Checks críticos** (deben pasar):
- ✅ [1] tenant_id columns exist → 7/7 tables
- ✅ [2] No NULL tenant_id values → 0 NULLs
- ✅ [3] Foreign key constraints → 7/7 FKs
- ✅ [8] Data integrity → 0 mismatches

---

## 🔍 Verificaciones Manuales (Opcional)

```sql
-- 1. Contar rows por tabla
SELECT 'import_batches' AS table, COUNT(*) FROM import_batches
UNION ALL
SELECT 'import_items', COUNT(*) FROM import_items
UNION ALL
SELECT 'import_attachments', COUNT(*) FROM import_attachments;

-- 2. Verificar tenant_id poblado
SELECT COUNT(*) FROM import_items WHERE tenant_id IS NULL;  -- debe ser 0

-- 3. Verificar JSONB
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'import_items' 
  AND column_name IN ('raw', 'normalized', 'errors');
-- Debe mostrar 'jsonb'

-- 4. Verificar índices GIN
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'import_items' 
  AND indexdef LIKE '%gin%';
-- Debe listar ix_import_items_normalized_gin, ix_import_items_raw_gin

-- 5. Test query JSONB
SELECT id, normalized->>'doc_type' AS doc_type
FROM import_items
WHERE normalized @> '{"doc_type": "invoice"}'::jsonb
LIMIT 5;
```

---

## 🛠️ Troubleshooting

### Error: "column tenant_id already exists"

**Causa**: Migración parcial aplicada previamente.

**Solución**:
```sql
-- Verificar estado actual
\d import_items

-- Si tenant_id existe pero no es NOT NULL:
ALTER TABLE import_items ALTER COLUMN tenant_id SET NOT NULL;

-- Si falta índice:
CREATE INDEX IF NOT EXISTS ix_import_items_tenant_id ON import_items(tenant_id);
```

### Error: "null value in column tenant_id violates not-null constraint"

**Causa**: Backfill incompleto.

**Solución**:
```sql
-- Identificar rows sin tenant_id
SELECT id, batch_id FROM import_items WHERE tenant_id IS NULL;

-- Backfill manual (ajustar según causa)
UPDATE import_items i
SET tenant_id = b.tenant_id
FROM import_batches b
WHERE i.batch_id = b.id AND i.tenant_id IS NULL;
```

### Error: "index ix_import_items_normalized_gin does not exist"

**Causa**: PostgreSQL versión < 9.4 o error en creación de índice.

**Solución**:
```sql
-- Crear manualmente
CREATE INDEX IF NOT EXISTS ix_import_items_normalized_gin 
  ON import_items USING gin (normalized);

CREATE INDEX IF NOT EXISTS ix_import_items_raw_gin 
  ON import_items USING gin (raw);
```

---

## 🔙 Rollback (Si algo sale mal)

```bash
# Opción 1: Usar script de rollback
python ops/scripts/apply_tenant_migration_imports.py --rollback

# Opción 2: Restaurar backup
pg_restore -d $DATABASE_URL -c backup_imports_*.pgcustom

# Opción 3: Rollback manual (SQL)
psql $DATABASE_URL -f ops/migrations/2025-10-17_050_add_tenant_id_to_imports/down.sql
```

**⚠️ Advertencia**: Rollback eliminará:
- Columnas `tenant_id` de import_items, import_attachments, import_ocr_jobs
- Conversión JSONB (revertirá a JSON)
- Todos los índices GIN y tenant-scoped

---

## 📝 Actualizar Código de App (Post-Migración)

### Ejemplo 1: Crear ImportBatch

```python
# ANTES
batch = ImportBatch(
    empresa_id=current_empresa_id,
    source_type="invoices",
    origin="api",
    created_by=current_user_id
)

# DESPUÉS
from uuid import UUID

batch = ImportBatch(
    tenant_id=UUID(current_tenant_id),  # ← NUEVO
    empresa_id=current_empresa_id,      # ← Mantener por ahora (deprecated)
    source_type="invoices",
    origin="api",
    created_by=current_user_id
)
```

### Ejemplo 2: Query con tenant_id

```python
# ANTES
items = db.query(ImportItem).filter(
    ImportItem.batch_id == batch_id
).all()

# DESPUÉS
items = db.query(ImportItem).filter(
    ImportItem.tenant_id == current_tenant_id,  # ← Filtro explícito
    ImportItem.batch_id == batch_id
).all()
```

### Ejemplo 3: Query JSONB (nuevo)

```python
# Query por doc_type (usa índice parcial)
invoices = db.query(ImportItem).filter(
    ImportItem.tenant_id == tenant_id,
    ImportItem.normalized['doc_type'].astext == 'invoice'
).all()

# Query por contención (usa GIN index)
ec_items = db.query(ImportItem).filter(
    ImportItem.tenant_id == tenant_id,
    ImportItem.normalized.contains({"country": "EC"})
).all()

# Query anidado
items_with_totals = db.query(ImportItem).filter(
    ImportItem.tenant_id == tenant_id,
    ImportItem.normalized['totals']['currency'].astext == 'USD'
).all()
```

---

## 🧪 Testing

### Test Unitario (Ejemplo)

```python
import pytest
from uuid import uuid4
from app.models.core.modelsimport import ImportBatch, ImportItem

def test_import_batch_with_tenant(db):
    tenant_id = uuid4()
    
    batch = ImportBatch(
        tenant_id=tenant_id,
        empresa_id=1,
        source_type="invoices",
        origin="api",
        created_by="test-user"
    )
    db.add(batch)
    db.commit()
    
    # Verificar tenant_id
    assert batch.tenant_id == tenant_id
    
    # Crear item
    item = ImportItem(
        tenant_id=tenant_id,
        batch_id=batch.id,
        idx=0,
        raw={"key": "value"},
        normalized={"doc_type": "invoice"},
        idempotency_key=f"{tenant_id}|batch|0"
    )
    db.add(item)
    db.commit()
    
    # Query por tenant
    items = db.query(ImportItem).filter(
        ImportItem.tenant_id == tenant_id
    ).all()
    
    assert len(items) == 1
    assert items[0].normalized['doc_type'] == 'invoice'
```

### Test de Aislamiento (Tenant Isolation)

```python
def test_tenant_isolation(db):
    tenant_a = uuid4()
    tenant_b = uuid4()
    
    # Crear items para ambos tenants
    item_a = create_import_item(db, tenant_a, doc_type="invoice")
    item_b = create_import_item(db, tenant_b, doc_type="receipt")
    
    # Query tenant A
    items = db.query(ImportItem).filter(
        ImportItem.tenant_id == tenant_a
    ).all()
    
    assert len(items) == 1
    assert items[0].id == item_a.id
    assert items[0].normalized['doc_type'] == 'invoice'
    
    # No debe ver items de tenant B
    assert item_b.id not in [i.id for i in items]
```

---

## ✅ Checklist Final

- [ ] Backup completo realizado
- [ ] Pre-requisitos verificados
- [ ] Dry-run revisado
- [ ] Migración aplicada sin errores
- [ ] Script de verificación pasa todos los checks
- [ ] Queries manuales de verificación ejecutadas
- [ ] Código de app actualizado (al menos en desarrollo)
- [ ] Tests unitarios actualizados y pasan
- [ ] Tests de integración con tenant_id funcionan
- [ ] Documentación interna actualizada

---

## 📞 Ayuda

Si encuentras problemas:

1. Revisa logs: `migration.log`
2. Ejecuta verificación: `verify_tenant_migration_imports.py`
3. Consulta troubleshooting arriba
4. Rollback si es crítico: `apply_tenant_migration_imports.py --rollback`
5. Contacta al equipo de DevOps/Backend

---

**Última actualización**: 2025-10-17  
**Versión**: 1.0  
**Compatibilidad**: PostgreSQL 12+, Python 3.10+, SQLAlchemy 2.0+
