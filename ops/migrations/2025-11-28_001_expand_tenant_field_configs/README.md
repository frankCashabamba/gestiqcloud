# Migration: Expand tenant_field_configs for Dynamic Field Configuration

## Description

Expands the existing `tenant_field_configs` table with new columns to support dynamic field configuration for imports, validations, and transformations.

This migration enables:
- **Aliases**: Multiple names for the same field (e.g., "precio", "pvp", "price" → `precio_venta`)
- **Field Types**: Type information (string, number, date, boolean, email, phone)
- **Validation**: Pattern matching (regex) and complex validation rules (JSON)
- **Transformation**: Code expressions to transform field values during import
- **Per-tenant & Per-module**: Configuration can be customized by tenant and entity type (module)

## Changes

### New Columns

| Column | Type | Purpose |
|--------|------|---------|
| `aliases` | JSONB | Array of alternative field names for detection during imports |
| `field_type` | VARCHAR(20) | Data type: 'string', 'number', 'date', 'boolean', 'email', 'phone', 'currency' |
| `validation_pattern` | VARCHAR(500) | Regex pattern for validation |
| `validation_rules` | JSONB | Complex validation rules: {min, max, decimal_places, etc.} |
| `transform_expression` | TEXT | JavaScript code as string to transform value: "parseFloat(v.replace(...))" |

## Table Structure After Migration

```
tenant_field_configs (expanded)
├── id (UUID) - Primary Key
├── tenant_id (UUID FK) - Foreign key to tenants
├── module (VARCHAR) - Entity type: 'products', 'clientes', 'proveedores'
├── field (VARCHAR) - Field name: 'precio_venta', 'email', 'sku'
├── visible (BOOLEAN)
├── required (BOOLEAN)
├── ord (SMALLINT)
├── label (TEXT)
├── help (TEXT)
├── aliases (JSONB) ← NEW
├── field_type (VARCHAR) ← NEW
├── validation_pattern (VARCHAR) ← NEW
├── validation_rules (JSONB) ← NEW
└── transform_expression (TEXT) ← NEW
```

## Example Data

### Products - Precio de Venta

```sql
INSERT INTO tenant_field_configs (
  tenant_id, module, field, visible, required, ord, label, help,
  aliases, field_type, validation_rules, transform_expression
)
VALUES (
  'uuid-tenant-123',
  'products',
  'precio_venta',
  true, true, 1,
  'Precio de Venta',
  'Precio al que se vende el producto',
  '["precio", "precio_venta", "pvp", "price", "sale_price"]'::jsonb,
  'number',
  '{"min": 0, "max": 999999, "decimal_places": 2}'::jsonb,
  'parseFloat(String(v).replace(/[^\d.-]/g, ""))'
);
```

## Backward Compatibility

- ✅ All new columns are NULLABLE (no breaking changes)
- ✅ Existing data remains untouched
- ✅ No need to modify application code immediately
- ✅ Can be adopted incrementally per tenant/module

## Rollback

Simply remove the new columns (see `down.sql`):

```sql
ALTER TABLE tenant_field_configs
  DROP COLUMN IF EXISTS transform_expression,
  DROP COLUMN IF EXISTS validation_rules,
  DROP COLUMN IF EXISTS validation_pattern,
  DROP COLUMN IF EXISTS field_type,
  DROP COLUMN IF EXISTS aliases;
```

## Prerequisites

- PostgreSQL 9.5+ (JSONB support)
- `tenant_field_configs` table must exist
- No data loss expected

## Applied Migrations

- `2025-11-21_000_complete_consolidated_schema` (prerequisite)

## Notes

- This is an **additive-only** migration
- Perfect for gradual adoption
- Can be combined with data seeding in separate migration
- No indexes added yet (can be optimized later based on query patterns)

---

**Status**: ✅ Ready for Production
**Date**: 2025-11-28
**Reversible**: Yes
