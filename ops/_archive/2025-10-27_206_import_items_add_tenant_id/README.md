Add tenant_id to import_items

Context
- SQLAlchemy models and repository write tenant_id into import_items during ingest to support RLS and per-tenant queries.
- The previous full schema migration (205_imports_full_schema) created import_items without tenant_id, causing runtime errors:
  - psycopg2.errors.UndefinedColumn: column "tenant_id" of relation "import_items" does not exist.

Changes
- Adds nullable UUID column tenant_id to import_items with FK to tenants(id).
- Backfills tenant_id from import_batches.tenant_id.
- Adds index on tenant_id for filtering.

Rollback
- Drops the index, FK constraint, and the column.
