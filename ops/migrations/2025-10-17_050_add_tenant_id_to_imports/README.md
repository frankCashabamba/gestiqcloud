# Migration: Add tenant_id to Imports Module

**Date**: 2025-10-17  
**Type**: Schema Enhancement  
**Scope**: Multi-tenant isolation for imports module

## Overview

This migration implements tenant-based isolation for the imports module by:
1. Adding `tenant_id` (UUID) to all imports tables
2. Converting JSON columns to JSONB for better performance
3. Creating tenant-scoped indexes and constraints
4. Maintaining backward compatibility with `empresa_id`

## Affected Tables

- `import_batches` *(already had tenant_id, adds composite indexes)*
- `import_items` ⭐ *primary migration target*
- `import_attachments`
- `import_mappings` *(already had tenant_id, JSONB conversion)*
- `import_item_corrections` *(already had tenant_id)*
- `import_lineage` *(already had tenant_id)*
- `import_ocr_jobs`

## Changes Per Table

### 1. import_items
- **New column**: `tenant_id UUID NOT NULL` → FK to `public.tenants(id)`
- **JSONB conversion**: `raw`, `normalized`, `errors` (JSON → JSONB)
- **New indexes**:
  - `ix_import_items_tenant_id`
  - `ix_import_items_tenant_dedupe` (tenant_id, dedupe_hash)
  - `ix_import_items_normalized_gin` (GIN index on normalized)
  - `ix_import_items_raw_gin` (GIN index on raw)
  - `ix_import_items_doc_type` (partial index on normalized->>'doc_type')
- **Updated constraint**: `UNIQUE(tenant_id, idempotency_key)` *(was idempotency_key only)*

### 2. import_attachments
- **New column**: `tenant_id UUID NOT NULL` → FK to `public.tenants(id)`
- **New index**: `ix_import_attachments_tenant_id`

### 3. import_ocr_jobs
- **New column**: `tenant_id UUID NOT NULL` → FK to `public.tenants(id)`
- **JSONB conversion**: `result` (JSON → JSONB)
- **New indexes**:
  - `ix_import_ocr_jobs_tenant_id`
  - `ix_import_ocr_jobs_tenant_status_created` (tenant_id, status, created_at)

### 4. import_mappings
- **JSONB conversion**: `mappings`, `transforms`, `defaults`, `dedupe_keys` (JSON → JSONB)
- **New indexes**:
  - `ix_import_mappings_tenant_source` (tenant_id, source_type)
  - `ix_import_mappings_mappings_gin` (GIN index on mappings)

### 5. import_batches
- **New index**: `ix_import_batches_tenant_status_created` (tenant_id, status, created_at)

## Backfill Strategy

1. **import_items**: Uses `import_batches.tenant_id` (via batch_id FK)
2. **import_attachments**: Uses `import_items.tenant_id` (via item_id FK)
3. **import_ocr_jobs**: Uses `public.tenants` mapping (via empresa_id)

```sql
-- Example backfill for import_items
UPDATE public.import_items i
SET tenant_id = b.tenant_id
FROM public.import_batches b
WHERE i.batch_id = b.id AND i.tenant_id IS NULL;
```

## Prerequisites

✅ `public.tenants` table must exist  
✅ `core_empresa.tenant_id` column must exist and be populated  
✅ All `import_batches` must have valid `tenant_id` values  
✅ PostgreSQL 12+ (for JSONB and GIN indexes)

## Applying the Migration

### Option 1: Using the Python Script (Recommended)

```bash
# Dry run (preview changes)
python ops/scripts/apply_tenant_migration_imports.py --dry-run

# Apply migration
python ops/scripts/apply_tenant_migration_imports.py

# Rollback if needed
python ops/scripts/apply_tenant_migration_imports.py --rollback
```

### Option 2: Using psql

```bash
psql $DATABASE_URL -f ops/migrations/2025-10-17_050_add_tenant_id_to_imports/up.sql
```

## Post-Migration Steps

### 1. Update Application Code

The SQLAlchemy models in `app/models/core/modelsimport.py` have been updated with:
- `tenant_id` columns (NOT NULL)
- `empresa_id` columns (marked as DEPRECATED)
- JSONB type hints with SQLite fallback

### 2. Verify Data Integrity

```sql
-- Check that all rows have tenant_id
SELECT COUNT(*) FROM import_items WHERE tenant_id IS NULL;  -- Should be 0
SELECT COUNT(*) FROM import_attachments WHERE tenant_id IS NULL;  -- Should be 0
SELECT COUNT(*) FROM import_ocr_jobs WHERE tenant_id IS NULL;  -- Should be 0

-- Verify tenant_id matches empresa_id mapping
SELECT i.id, i.tenant_id, t.id AS expected_tenant_id
FROM import_ocr_jobs i
JOIN core_empresa e ON e.id = i.empresa_id
JOIN tenants t ON t.empresa_id = e.id
WHERE i.tenant_id != t.id;  -- Should be empty
```

### 3. Test Queries with JSONB

```sql
-- Query by doc_type (uses GIN index)
SELECT * FROM import_items 
WHERE normalized->>'doc_type' = 'expense_receipt' 
  AND tenant_id = 'your-tenant-uuid-here';

-- Query with containment (uses GIN index)
SELECT * FROM import_items 
WHERE normalized @> '{"country": "EC"}'::jsonb
  AND tenant_id = 'your-tenant-uuid-here';
```

### 4. Enable RLS Policies (if not already done)

See migration `2025-10-10_035_rls_policies` for RLS setup.

```sql
-- Example RLS policy for import_items
ALTER TABLE import_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY p_import_items_tenant ON import_items
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

## Backward Compatibility

- **empresa_id** columns are preserved and marked as DEPRECATED
- Will be removed in **v2.0** (approximately 2 releases from now)
- Existing queries using `empresa_id` will continue to work
- New code should use `tenant_id` exclusively

## Performance Notes

### JSONB vs JSON
- **GIN indexes** enable fast containment queries (`@>`, `?`, `?&`, `?|`)
- **Expression indexes** on `->>'doc_type'` speed up common filters
- **Storage**: JSONB uses more disk space but offers better query performance

### Index Usage Examples

```sql
-- Uses ix_import_items_tenant_dedupe
SELECT * FROM import_items 
WHERE tenant_id = ? AND dedupe_hash = ?;

-- Uses ix_import_items_normalized_gin
SELECT * FROM import_items 
WHERE normalized @> '{"totals": {"currency": "USD"}}'::jsonb;

-- Uses ix_import_items_doc_type (partial index)
SELECT * FROM import_items 
WHERE normalized->>'doc_type' = 'invoice';
```

## Rollback Instructions

If you need to rollback this migration:

```bash
# Using script
python ops/scripts/apply_tenant_migration_imports.py --rollback

# Using psql
psql $DATABASE_URL -f ops/migrations/2025-10-17_050_add_tenant_id_to_imports/down.sql
```

⚠️ **Warning**: Rollback will:
- Drop `tenant_id` columns from `import_items`, `import_attachments`, `import_ocr_jobs`
- Convert JSONB back to JSON (losing GIN indexes)
- Restore old `UNIQUE(idempotency_key)` constraint

## Testing

### Unit Tests
Update tests to provide `tenant_id` when creating import records:

```python
# Before
batch = ImportBatch(empresa_id=1, source_type="invoices", ...)

# After
batch = ImportBatch(
    tenant_id="your-tenant-uuid",
    empresa_id=1,  # Still required but deprecated
    source_type="invoices",
    ...
)
```

### Integration Tests
Verify tenant isolation:

```python
def test_tenant_isolation():
    # Create items for different tenants
    item1 = create_import_item(tenant_id=tenant_a_id)
    item2 = create_import_item(tenant_id=tenant_b_id)
    
    # Query with tenant_a context
    set_tenant(db, tenant_a_id)
    items = db.query(ImportItem).all()
    
    # Should only see tenant_a items
    assert len(items) == 1
    assert items[0].id == item1.id
```

## Migration Timeline

- **Phase 1** (Current): Add tenant_id, maintain empresa_id
- **Phase 2** (1-2 releases): Deprecation warnings in logs
- **Phase 3** (v2.0): Remove empresa_id columns

## Files Modified

### Created
- `ops/migrations/2025-10-17_050_add_tenant_id_to_imports/up.sql`
- `ops/migrations/2025-10-17_050_add_tenant_id_to_imports/down.sql`
- `ops/migrations/2025-10-17_050_add_tenant_id_to_imports/meta.yaml`
- `ops/migrations/2025-10-17_050_add_tenant_id_to_imports/README.md`
- `ops/scripts/apply_tenant_migration_imports.py`

### Updated
- `apps/backend/app/models/core/modelsimport.py`
  - Added `tenant_id` to all import models
  - Converted JSON to JSONB with SQLite fallback
  - Updated indexes and constraints
  - Added deprecation comments for `empresa_id`

## Support

For issues or questions:
1. Check prerequisites are met
2. Run with `--dry-run` to preview changes
3. Review logs in `ops/migrations/migration.log` (if exists)
4. Contact DevOps team

---

**Status**: ✅ Ready for deployment  
**Risk**: Low (backward compatible, non-breaking)  
**Estimated Duration**: 2-5 minutes (depends on data volume)
