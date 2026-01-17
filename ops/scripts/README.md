# Scripts de operaciones

## Migraciones
- `migrate_all_migrations_idempotent.py`: aplica migraciones SQL en orden, saltando las ya aplicadas (requiere `DATABASE_URL`).
- `migrate_all_migrations.py`: versión simple no idempotente.
- `generate_migration_from_models.py`: genera SQL desde modelos actuales para comparar.

## Checks
- `check_endpoints.py`: smoke test de endpoints FE/BE (usado en CI backend). Ajustar URLs/env antes de ejecutar.
- `check_db_migrations_coverage.py`: compara tablas public en DB vs migraciones (neto create/drop). Usa `DATABASE_URL`.

## Notas
- Ejecutar con el entorno virtual adecuado (`pip install -r ops/requirements.txt`).
- Para backups/restauración, usar `pg_dump`/`psql` (ver `docs/datos-migraciones.md`).
