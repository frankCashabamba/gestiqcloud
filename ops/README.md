# Operations / Infra

Infrastructure assets, SQL migrations, and support scripts for deployment and maintenance.

## Structure
- `ci/`: pipeline helpers and migration checks.
- `dns/`: Cloudflare DNS configuration and exported records.
- `migrations/`: manual SQL migrations, including the consolidated snapshot in `2025-11-21_000_complete_consolidated_schema`.
- `scripts/`: automation for idempotent migrations, SQL generation, and endpoint checks.
- `systemd/`: service unit examples such as `gestiq-worker-imports.service`.
- `requirements.txt`: Python dependencies for ops scripts.

## CI/CD
- `.github/workflows/ci.yml` detects frontend/backend changes and runs:
- Backend: dependency install, `test.db` recreation, `Base.metadata.create_all`, pytest, and `ops/scripts/check_endpoints.py`.
- Frontend: `npm ci` or `npm install`, `npm run typecheck`, and `npm run build` for admin and tenant.

## Key Scripts
- `migrate_all_migrations_idempotent.py`: applies SQL migrations in order and skips already tracked ones. Requires `DATABASE_URL`.
- `migrate_all_migrations.py`: simple non-idempotent runner.
- `generate_migration_from_models.py`: generates SQL from the current models for comparison.
- `check_endpoints.py`: backend/frontend smoke test used in CI.

## SQL Migrations
- `migrations/2025-11-21_000_complete_consolidated_schema/`: full schema snapshot with `up.sql`, `down.sql`, and supporting notes.
- Apply migrations through the scripts above and take a database backup first, for example with `pg_dump`.

## DNS And Deployments
- `dns/*.txt`: exported Cloudflare records for `gestiqcloud.com` and related subdomains.
- API deployment runs on Render. See the root `render.yaml`.
- Worker deployment details live under `workers/README.md`.

## Systemd / Services
- Service unit examples are provided for workers and background jobs.
- Adjust paths and environment variables before using them on servers.

## Backups And Security
- Back up the database before manual migration work.
- Keep secrets in environment variables and do not commit `.env` files.
- Review allowed CORS and worker domains before exposing endpoints publicly.

## Pending Docs
- Add an exact Render and Cloudflare deployment runbook.
- Add a post-migration verification checklist.
