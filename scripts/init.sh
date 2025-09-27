#!/usr/bin/env bash
set -euo pipefail

cmd=${1:-help}

case "$cmd" in
  up)
    docker compose up -d --build ;;
  up-dev)
    docker compose up --build ;;
  down)
    docker compose down -v ;;
  rebuild)
    docker compose build --no-cache ;;
  logs)
    svc=${2:-backend}
    docker compose logs -f "$svc" ;;
  logs-all)
    docker compose logs -f ;;
  typecheck)
    (cd apps/admin && npm ci && npm run typecheck) && \
    (cd apps/tenant && npm ci && npm run typecheck) ;;
  migrate)
    action=${2:-up}
    dir=${3:-ops/migrations/2025-09-22_004_imports_batch_pipeline}
    if [ -z "${DB_DSN:-}" ]; then
      echo "Set DB_DSN env var with your Postgres DSN" >&2
      exit 1
    fi
    python scripts/py/apply_migration.py --dsn "$DB_DSN" --dir "$dir" --action "$action" ;;
  schema-check)
    if [ -z "${DB_DSN:-}" ]; then
      echo "Set DB_DSN env var with your Postgres DSN" >&2
      exit 1
    fi
    python scripts/py/check_schema.py --dsn "$DB_DSN" ;;
  auto-migrate)
    if [ -z "${DB_DSN:-}" ]; then
      echo "Set DB_DSN env var with your Postgres DSN" >&2
      exit 1
    fi
    python scripts/py/auto_migrate.py --dsn "$DB_DSN" ;;
  baseline)
    dsn=${DB_DSN:-$DATABASE_URL}
    if [ -z "${dsn:-}" ]; then
      echo "Set DB_DSN or DATABASE_URL with your Postgres DSN" >&2
      exit 1
    fi
    python scripts/py/make_baseline.py ;;
  schema-explain)
    dsn=${DB_DSN:-$DATABASE_URL}
    if [ -z "${dsn:-}" ]; then
      echo "Set DB_DSN or DATABASE_URL with your Postgres DSN" >&2
      exit 1
    fi
    sqlFile='ops/sql/check_imports_indexes.sql'
    if [ ! -f "$sqlFile" ]; then
      echo "Not found: $sqlFile" >&2
      exit 1
    fi
    psql "$dsn" -f "$sqlFile" ;;
  alembic-draft)
    if [ -z "${DATABASE_URL:-}" ]; then
      echo "Set DATABASE_URL for Alembic (e.g., postgresql://user:pass@host:5432/db)" >&2
      exit 1
    fi
    python scripts/py/alembic_draft.py ;;
  local)
    docker compose up -d db
    : "${IMPORTS_ENABLED:=1}"
    # Imports validation flags for dev (toggle as needed)
    : "${IMPORTS_VALIDATE_CURRENCY:=true}"
    : "${IMPORTS_REQUIRE_CATEGORIES:=true}"
    : "${DB_DSN:=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev}"
    : "${FRONTEND_URL:=http://localhost:8081}"
    : "${DATABASE_URL:=$DB_DSN}"
    : "${TENANT_NAMESPACE_UUID:=$(python - <<'PY'
import uuid, os
print(os.environ.get('TENANT_NAMESPACE_UUID') or uuid.uuid4())
PY
)}"
    python scripts/py/auto_migrate.py --dsn "$DB_DSN"
    python scripts/py/check_schema.py --dsn "$DB_DSN"
    export PYTHONPATH="$PWD:$PWD/apps:$PWD/apps/backend"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir "${PWD}/apps/backend" ;;
  compose-min)
    docker compose up -d db migrations backend ;;
  compose-backend)
    docker compose up -d backend ;;
  compose-all)
    docker compose up -d db migrations backend admin tenant ;;
  *)
    echo "Usage: $0 {up|down|rebuild|logs [svc]|typecheck|migrate [up|down] [dir]|schema-check|schema-explain|auto-migrate|alembic-draft|baseline|local|compose-min|compose-backend|compose-all}" ;;
esac


