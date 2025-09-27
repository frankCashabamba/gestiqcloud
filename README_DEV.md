Developer Setup Guide

Prerequisites
- Docker + Docker Compose
- Python 3.11+ (for running scripts locally)
- Node.js 18+ (if working on admin/tenant)

Environment (recommended defaults)
- Backend env (.env or session):
  - DB_DSN=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev
  - IMPORTS_ENABLED=1

Project Scripts (shortcuts)
- PowerShell (Windows): `scripts/init.ps1`
- Bash (Linux/macOS): `./scripts/init.sh`

Common Commands
- Start full stack with migrations (Docker):
  - `docker compose up -d --build`
  - Services: db → migrations (applies SQL) → backend → admin/tenant
- Minimal stack (DB + migrations + backend):
  - PS: `scripts/init.ps1 compose-min`
  - Bash: `./scripts/init.sh compose-min`
- Backend only (assumes migrations already ran):
  - PS: `scripts/init.ps1 compose-backend`
  - Bash: `./scripts/init.sh compose-backend`
- Full stack (db + migrations + backend + admin + tenant):
  - PS: `scripts/init.ps1 compose-all`
  - Bash: `./scripts/init.sh compose-all`

Local (backend on host, DB in Docker)
1) Start DB: `docker compose up -d db`
2) Apply migrations + check schema:
   - PS: `scripts/init.ps1 auto-migrate` then `scripts/init.ps1 schema-check`
   - Bash: `./scripts/init.sh auto-migrate` then `./scripts/init.sh schema-check`
3) Run backend with hot-reload:
   - `cd apps/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir apps/backend`

Imports Module (batch staging → validate → promote)
- Endpoints (prefix `/api/v1/imports`):
  - POST `/batches` → create batch { source_type, origin, file_key?, mapping_id? }
  - POST `/batches/{id}/ingest` → { rows[], mapping_id?, transforms?, defaults? }
  - GET `/batches/{id}/items` → list items (status=, q=, with=lineage)
  - PATCH `/batches/{id}/items/{itemId}` → { field, value } (saves correction + revalidates)
  - POST `/batches/{id}/validate` → revalidate
  - POST `/batches/{id}/promote` → promote (idempotent)
  - GET `/batches/{id}/errors.csv` → idx,campo,error,valor
- Mappings (plantillas):
  - CRUD under `/mappings` (create/list/get/update/clone/delete)
  - If `mapping_id` is set: rows are normalized with mappings/transforms/defaults

Migrations & Schema
- Auto-migrate (applies all `ops/migrations/*`):
  - PS: `scripts/init.ps1 auto-migrate`
  - Bash: `./scripts/init.sh auto-migrate`
- Check schema (fails if missing tables/columns/indexes):
  - PS: `scripts/init.ps1 schema-check`
  - Bash: `./scripts/init.sh schema-check`
- One-off migration (apply/rollback a folder):
  - PS: `scripts/init.ps1 migrate up ops/migrations/<folder>`
  - Bash: `./scripts/init.sh migrate up ops/migrations/<folder>`

Health & Diagnostics
- Backend healthcheck (Docker):
  - If `IMPORTS_ENABLED=1` and `DB_DSN` present, uses `scripts/py/bootstrap_imports.py --check-only`.
  - Fallback: HTTP `GET /api/v1/imports/health`.
- Manual check:
  - `curl http://localhost:8000/api/v1/imports/health`

Testing
- Run backend tests:
  - `PYTHONPATH="$PWD;$PWD/apps" pytest -q apps/backend/app/tests`
- Notes:
  - Tests use SQLite; some Postgres-only tables are pruned in conftest.
  - Two tests are xfailed by design (admin CSRF/routers not mounted in minimal env).

Alembic (autogenerate drafts)
- Purpose: generate draft revisions from SQLAlchemy models for review.
- Location: `apps/backend/alembic` (env.py uses `app.db.base.target_metadata`).
- Generate a draft (requires `DATABASE_URL` pointing to Postgres):
  - PowerShell: `setx DATABASE_URL "postgresql://user:pass@localhost:5432/db"` (or set for session)
  - Run: `python scripts/py/alembic_draft.py`
- Output: revision under `apps/backend/alembic/versions/`.
- Process: review the diff, then translate into `ops/migrations/<folder>/{up,down}.sql` for production.
- Do not auto-apply alembic revisions in production; use `ops/migrations` pipeline.

Baseline (inicializar prod desde esquema actual)
- Genera un baseline limpio desde tu DB local (Postgres):
  - Exporta DSN: `DB_DSN=postgresql://user:pass@localhost:5432/db`
  - PS: `scripts/init.ps1 baseline` | Bash: `./scripts/init.sh baseline`
- El script usa `pg_dump --schema-only --no-owner --no-privileges` y limpia:
  - SET/OWNER/GRANT/REVOKE/COMMENT/CREATE EXTENSION del dump (se añaden extensiones curadas).
  - Evita crear `schema public` y deja `uuid-ossp`/`pgcrypto` idempotentes al inicio.
- Revisa `ops/migrations/2025-09-22_000_baseline_full_schema/up.sql` y aplica en entornos vírgenes.

Conventions
- Python: 4 spaces; snake_case; classes in PascalCase. Black/Isort/Ruff if configured.
- TypeScript/React: 2 spaces; camelCase; components in PascalCase; ESLint/Prettier if present.
- TS aliases: `@shared/*` and `@/*`.

Troubleshooting
- Imports endpoints 404 in tests/dev: ensure `IMPORTS_ENABLED=1`.
- Health failing due to schema: run auto-migrate and schema-check.
- UUID/JSONB issues in tests: tests run on SQLite; Postgres-only parts are excluded automatically.



Validation Flags (env)
- Backend reads two simple feature flags for the imports validators:
  - IMPORTS_VALIDATE_CURRENCY (default: 	rue)
    - When 	rue, invoices validate ISO-4217 currency codes (e.g., EUR).
  - IMPORTS_REQUIRE_CATEGORIES (default: 	rue)
    - When 	rue, expenses/receipts require a non-empty category/categoria.
- Example .env to relax in dev:
  - IMPORTS_VALIDATE_CURRENCY=false
  - IMPORTS_REQUIRE_CATEGORIES=false
- Implementation:
  - Flags consumed in pp.modules.imports.application.use_cases._validate_by_type and enforced in alidators.py.
