# Data And Migrations

## Strategy
- The active migration source of truth is `ops/migrations`.
- The revision scaffold folder `apps/backend/revision_scaffold` is scaffold-only and `apps/backend/revision_scaffold/versions` may remain intentionally empty.
- Support scripts under `ops/scripts` orchestrate idempotent SQL migrations and generate SQL from models when needed.

## SQL Migrations (Active Workflow)
- Main runner: `python ops/scripts/migrate_all_migrations_idempotent.py`
- Fallback runner: `python ops/scripts/migrate_all_migrations.py`
- Tracking table: `_migrations`
- Consolidated example: `ops/migrations/2025-11-21_000_complete_consolidated_schema/`

## Recommended Order
1. Apply base or snapshot SQL migrations first when needed.
2. Apply pending SQL migrations with the idempotent runner.
3. Register any new migration folders in the operational workflow and verify `_migrations`.

## Support Scripts (`ops/scripts`)
- `migrate_all_migrations_idempotent.py`: applies SQL migrations in order and skips already tracked entries. Requires `DATABASE_URL`.
- `migrate_all_migrations.py`: simple non-idempotent runner.
- `generate_migration_from_models.py`: generates SQL from the current models for DB comparison.
- `check_endpoints.py`: backend/frontend smoke test used in CI.

## Migration Job (Render)
- The migration UI button can trigger the Render job configured in `RENDER_MIGRATE_JOB_ID`.
- Current usage is manual after schema changes.
- Status may appear as unknown until a run has been triggered at least once.

## Rollback And Backups
- Before manual SQL work, create a database backup with `pg_dump`.
  ```bash
  pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M).sql
  ```
- Restore with care because it overwrites data.
  ```bash
  psql "$DATABASE_URL" < backup_20250101_1200.sql
  ```
- Use `down.sql` only when rollback is understood and safe.
- If you revert SQL changes manually, validate data compatibility first.

## Post-Migration Checklist
- Health checks are green: `/health`, `/ready`
- Critical module queries succeed
- Key tables contain expected data and constraints
- Application and migration logs show no unexpected errors
- If RLS is enabled, tenant isolation behaves as expected
