# Database Pipeline & Migrations

- Run CI checks locally:
  - `python ops/ci/checks.py`
  - `python ops/ci/migrate.py`
- Migrations folder under `ops/migrations/*`.
- Scripts under `ops/scripts/*` for db operations.
## Ops Quickstart

- DEV (Docker Compose)
  - `docker compose up -d --build` → corre el servicio `migrations` (bootstrap) y luego `backend`.
  - Health: `curl http://localhost:8000/api/v1/imports/health` (si `IMPORTS_ENABLED=1`).

- Manual (local)
  - `DB_DSN=postgresql://user:pass@localhost:5432/db ./scripts/init.sh auto-migrate`
  - `DB_DSN=postgresql://user:pass@localhost:5432/db ./scripts/init.sh schema-check`

- Producción (pipeline sugerido)
  - `python scripts/py/bootstrap_imports.py --dsn $DB_DSN --dir ops/migrations`
  - `python scripts/py/bootstrap_imports.py --dsn $DB_DSN --check-only` (verificación)
  - Desplegar backend/admin/tenant tras migraciones OK.
