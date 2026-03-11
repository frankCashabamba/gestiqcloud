# Operations Scripts

## Migrations
- `migrate_all_migrations_idempotent.py`: applies SQL migrations in order and skips already tracked ones. Requires `DATABASE_URL`.
- `migrate_all_migrations.py`: simple non-idempotent runner.
- `generate_migration_from_models.py`: generates SQL from the current models for comparison.

## Checks
- `check_endpoints.py`: backend/frontend smoke test used in CI. Adjust URLs and environment variables before running it.
- `check_db_migrations_coverage.py`: compares `public` DB tables against the migration set after net create/drop resolution. Requires `DATABASE_URL`.

## Notes
- Run these scripts from the correct virtual environment, for example after `pip install -r ops/requirements.txt`.
- Use `pg_dump` and `psql` for backup and restore workflows.
