# Ops

This directory hosts database migrations, CI helpers, and operational scripts.

- migrations/: timestamped, declarative migrations (SQL/py) grouped by folder
- ci/: lightweight checks and a smoke migration runner for CI
- scripts/: convenience scripts for local/ops usage

Refer to .github/workflows/db-pipeline.yml for how CI invokes these tools.

## Applying migrations locally

- PostgreSQL (manual):
  - Apply: `psql -d <db> -f ops/migrations/<folder>/up.sql`
  - Rollback: `psql -d <db> -f ops/migrations/<folder>/down.sql`

- Python helper:
  - `python scripts/py/apply_migration.py --dsn postgresql://user:pass@localhost/dbname --dir ops/migrations/2025-09-22_004_imports_batch_pipeline --action up`
  - Or rollback with `--action down`.

## Imports pipeline migration

- Folder: `ops/migrations/2025-09-22_004_imports_batch_pipeline`
- Creates: import_batches, import_items (+idx), import_mappings, import_item_corrections, import_lineage
- Alters: auditoria_importacion (adds batch_id, item_id)
