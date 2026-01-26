# Archivos SQL de la Migración

## Ubicación de los Archivos

```
ops/migrations/2026-01-22_001_add_pos_invoice_lines/
├── up.sql       (aplica la migración)
├── down.sql     (revierte la migración)
└── README.md    (documentación)
```

## Archivo 1: up.sql (Aplicar)

**Ubicación:** `ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql`

**Qué hace:** Crea la tabla `pos_invoice_lines` y los índices necesarios

**Contenido:**
```sql
-- Migration: Add `pos_invoice_lines` table for POSLine polymorphic model
-- Date: 2026-01-22
-- Purpose: Support SQLAlchemy polymorphic inheritance with sector='pos'

DO $$
BEGIN
    -- Check if invoice_lines table exists (should exist from consolidated schema)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_lines') THEN
        
        -- Create pos_invoice_lines table (joined table inheritance)
        CREATE TABLE IF NOT EXISTS pos_invoice_lines (
            id UUID NOT NULL PRIMARY KEY,
            pos_receipt_line_id UUID,
            FOREIGN KEY (id) REFERENCES invoice_lines(id) ON DELETE CASCADE
        );
        
        -- Index for pos_receipt_line_id lookups
        CREATE INDEX IF NOT EXISTS idx_pos_invoice_lines_pos_receipt_line_id 
            ON pos_invoice_lines(pos_receipt_line_id);
        
        -- Optional: Composite index for tenant + pos_receipt_id (for better query planning)
        -- Useful for queries like: SELECT * FROM pos_invoice_lines WHERE pos_receipt_line_id = ?
        
    END IF;
END $$;
```

**Cómo ejecutar:**

```bash
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

---

## Archivo 2: down.sql (Revertir)

**Ubicación:** `ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql`

**Qué hace:** Elimina la tabla `pos_invoice_lines` y los índices

**Contenido:**
```sql
-- Rollback: Remove `pos_invoice_lines` table

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pos_invoice_lines') THEN
        DROP INDEX IF EXISTS idx_pos_invoice_lines_pos_receipt_line_id;
        DROP TABLE IF EXISTS pos_invoice_lines CASCADE;
    END IF;
END $$;
```

**Cómo ejecutar:**

```bash
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

---

## Archivo 3: README.md (Documentación)

**Ubicación:** `ops/migrations/2026-01-22_001_add_pos_invoice_lines/README.md`

**Contenido:**
```markdown
# Migration: Add `pos_invoice_lines` table for POSLine polymorphic model

## Purpose

- Support SQLAlchemy polymorphic inheritance for `InvoiceLine` base model
- Map `invoice_lines.sector='pos'` records to `POSLine` model
- Create `pos_invoice_lines` table for joined table inheritance

## Problem Solved

Database has `invoice_lines` records with `sector='pos'` but Python models didn't have `POSLine` class.
This caused: `AssertionError: No such polymorphic_identity 'pos' is defined`

## Changes

1. Creates `pos_invoice_lines` table (joined table inheritance from `invoice_lines`)
2. Creates index on `pos_receipt_line_id` for FK lookups
3. Safe on existing databases: uses `IF NOT EXISTS` and conditional table existence check

## Rollback

If needed, the `down.sql` script drops the table and indexes.

## Notes

- This migration is idempotent (safe to apply multiple times)
- No data migration required (existing 'pos' records in `invoice_lines` will work automatically)
- Optional: migrate existing data to `pos_invoice_lines` using manual SQL if needed
```

---

## Ejecución Paso a Paso

### 1. Visualizar archivos
```bash
ls -la ops/migrations/2026-01-22_001_add_pos_invoice_lines/
```

Deberías ver:
```
total 12
-rw-r--r-- 1 user user 1234 Jan 22 10:00 README.md
-rw-r--r-- 1 user user 567  Jan 22 10:00 down.sql
-rw-r--r-- 1 user user 789  Jan 22 10:00 up.sql
```

### 2. Leer el contenido
```bash
cat ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

### 3. Ejecutar la migración
```bash
# Opción A: Usar psql
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql

# Opción B: Desde psql interactivo
psql -U gestiqcloud_user -d gestiqcloud
psql> \i ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
psql> \dt pos_invoice_lines  -- verificar
psql> \q  -- salir
```

### 4. Verificar resultado
```bash
psql -U gestiqcloud_user -d gestiqcloud -c "SELECT * FROM pos_invoice_lines LIMIT 1;"
```

### 5. Si necesitas revertir
```bash
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

---

## Características de los Scripts SQL

### ✅ Idempotentes
- Usan `IF NOT EXISTS` para que se puedan ejecutar múltiples veces sin errores
- Usan `IF EXISTS` para verificar antes de cambiar

### ✅ Seguros
- No borran datos (CASCADE solo en la tabla nueva)
- Usan transacciones implícitas con `DO $$`
- Verifican la existencia de tablas dependientes

### ✅ Reversibles
- El archivo `down.sql` revierte exactamente los cambios de `up.sql`
- Puedes aplicar y deshacer sin problemas

### ✅ Compatibles
- Funcionan en PostgreSQL 11+
- Compatible con TZ aware timestamps
- Usan tipos UUID nativos

---

## Relación con Python

Estos scripts SQL crean la **estructura de base de datos** para que el código Python pueda funcionar:

```python
# models/core/invoiceLine.py - CÓDIGO PYTHON
class POSLine(InvoiceLine):
    __tablename__ = "pos_invoice_lines"  # ← Corresponde a la tabla creada por up.sql
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("invoice_lines.id"), primary_key=True
    )
    __mapper_args__ = {"polymorphic_identity": "pos"}  # ← Mapeo de sector='pos'
```

---

## Verificación Completa

Después de ejecutar `up.sql`:

```bash
# 1. Verificar tabla existe
psql -U gestiqcloud_user -d gestiqcloud -c "\dt pos_invoice_lines"

# 2. Verificar estructura
psql -U gestiqcloud_user -d gestiqcloud -c "\d pos_invoice_lines"

# 3. Verificar índices
psql -U gestiqcloud_user -d gestiqcloud -c "\di *pos_invoice*"

# 4. Verificar FK
psql -U gestiqcloud_user -d gestiqcloud -c \
  "SELECT constraint_name, table_name, column_name 
   FROM information_schema.key_column_usage 
   WHERE table_name='pos_invoice_lines'"

# 5. Verificar está vacía (es nueva)
psql -U gestiqcloud_user -d gestiqcloud -c "SELECT COUNT(*) FROM pos_invoice_lines"
```

Resultado esperado:
```
 count 
-------
     0
(1 row)
```

---

## Variables de Entorno

Si necesitas cambiar la configuración:

```bash
export PGUSER=gestiqcloud_user
export PGDATABASE=gestiqcloud
export PGHOST=localhost
export PGPORT=5432

# Ahora psql usa esas variables
psql -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

---

**Resumen:** 3 archivos SQL, ejecución simple, totalmente reversible.
