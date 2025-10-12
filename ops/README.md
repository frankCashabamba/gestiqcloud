# Ops

This directory hosts database migrations, CI helpers, and operational scripts.

- migrations/: timestamped, declarative migrations (SQL/py) grouped by folder
- ci/: lightweight checks and a smoke migration runner for CI
- scripts/: convenience scripts for local/ops usage

Refer to .github/workflows/db-pipeline.yml for how CI invokes these tools.

## Production Deploy Flow (Render + Cloudflare)

Goal: keep web startup fast and run DB changes only when needed.

1) Web Service (apps/backend)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Do NOT run migrations on boot (keep `RUN_ALEMBIC=0`, `RUN_LEGACY_MIGRATIONS=0`, `RUN_RLS_APPLY=0`).
- Health: `/health` (FastAPI) and `/health` on API host via Worker.

2) Migrations Job (Render)
- Job name: `gestiqcloud-migrate` (see `render.yaml`).
- Command: only upgrades Alembic if pending; then applies RLS defaults/policies idempotently.
- Env: `DATABASE_URL`, `ENV=production`, `RLS_SCHEMAS=public`, `RLS_SET_DEFAULT=1`.

3) CI trigger (GitHub Actions)
- Workflow: `.github/workflows/migrate-on-migrations.yml` runs only when files change in:
  - `apps/backend/alembic/versions/**`
  - `ops/migrations/**`
  - `scripts/py/apply_rls.py`
- Calls Render Jobs API with secrets `RENDER_API_KEY` and `RENDER_MIGRATE_JOB_ID`.

4) Cloudflare Worker (Edge Gateway)
- Routes include `api.gestiqcloud.com/*` and admin/www `*/api/*`.
- Accepts clean `/v1/*` and rewrites to backend `/api/v1/*`.
- CORS allow-list and secure Set-Cookie rewriting for `.gestiqcloud.com`.

5) Backend env (prod)
- `PUBLIC_API_ORIGIN=https://api.gestiqcloud.com`
- `ADMIN_URL=https://admin.gestiqcloud.com`
- `FRONTEND_URL=https://www.gestiqcloud.com`
- `ALLOWED_HOSTS=["api.gestiqcloud.com","*.onrender.com"]`
- `CORS_ORIGINS=["https://gestiqcloud.com","https://www.gestiqcloud.com","https://admin.gestiqcloud.com"]`
- `CORS_ALLOW_ORIGIN_REGEX=^https://(www\.)?(gestiqcloud\.com|admin\.gestiqcloud\.com|gestiqcloud-(admin|tenant)\.onrender\.com)$`
- `COOKIE_DOMAIN=.gestiqcloud.com`, `COOKIE_SAMESITE=none`, `COOKIE_SECURE=true`

6) Frontends (Vite)
- `VITE_API_URL=https://api.gestiqcloud.com`
- `VITE_ADMIN_ORIGIN=https://admin.gestiqcloud.com`
- `VITE_TENANT_ORIGIN=https://www.gestiqcloud.com`
- HTTP client sends cookies (Axios `withCredentials: true` / fetch `credentials: 'include'`).

## Applying migrations locally

- PostgreSQL (manual):
  - Apply: `psql -d <db> -f ops/migrations/<folder>/up.sql`
  - Rollback: `psql -d <db> -f ops/migrations/<folder>/down.sql`

- Python helper:
  - `python scripts/py/apply_migration.py --dsn postgresql://user:pass@localhost/dbname --dir ops/migrations/2025-09-22_004_imports_batch_pipeline --action up`
  - Or rollback with `--action down`.

## API Gateway

Backend can be fronted by a Cloudflare Worker at `api.gestiqcloud.com` to:
- Enforce restrictive CORS with credentials
- Harden cookies (Domain, Secure, HttpOnly, SameSite)
- Propagate `X-Request-Id` and security headers

See `workers/README.md` for configuration, `wrangler publish`, route setup and curl tests.

## Imports pipeline migration

- Folder: `ops/migrations/2025-09-22_004_imports_batch_pipeline`
- Creates: import_batches, import_items (+idx), import_mappings, import_item_corrections, import_lineage
- Alters: auditoria_importacion (adds batch_id, item_id)
