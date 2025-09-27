param(
  [Parameter(Position=0)][string]$cmd = "help",
  [Parameter(Position=1)][string]$arg1 = "backend",
  [Parameter(Position=2)][string]$arg2 = ""
)

switch ($cmd) {
  'up' { docker compose up -d --build }
  'up-dev' { docker compose up --build }
  'down' { docker compose down -v }
  'rebuild' { docker compose build --no-cache }
  'logs' { docker compose logs -f $arg1 }
  'logs-all' { docker compose logs -f }
  'typecheck' {
    pushd apps/admin; npm ci; npm run typecheck; popd
    pushd apps/tenant; npm ci; npm run typecheck; popd
  }
  'migrate' {
    $action = if ($arg1) { $arg1 } else { 'up' }
    $dir = if ($arg2) { $arg2 } else { 'ops/migrations/2025-09-22_004_imports_batch_pipeline' }
    $dsn = $env:DB_DSN
    if (-not $dsn) { Write-Error 'Set DB_DSN env var with your Postgres DSN.'; break }
    python scripts/py/apply_migration.py --dsn $dsn --dir $dir --action $action
  }
  'baseline' {
    $dsn = if ($env:DB_DSN) { $env:DB_DSN } else { $env:DATABASE_URL }
    if (-not $dsn) { Write-Error 'Set DB_DSN or DATABASE_URL with your Postgres DSN.'; break }
    python scripts/py/make_baseline.py
  }
  'schema-explain' {
    $dsn = if ($env:DB_DSN) { $env:DB_DSN } else { $env:DATABASE_URL }
    if (-not $dsn) { Write-Error 'Set DB_DSN or DATABASE_URL with your Postgres DSN.'; break }
    $sqlFile = 'ops/sql/check_imports_indexes.sql'
    if (-not (Test-Path $sqlFile)) { Write-Error "Not found: $sqlFile"; break }
    psql $dsn -f $sqlFile
  }
  'schema-check' {
    $dsn = $env:DB_DSN
    if (-not $dsn) { Write-Error 'Set DB_DSN env var with your Postgres DSN.'; break }
    python scripts/py/check_schema.py --dsn $dsn
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  'auto-migrate' {
    $dsn = $env:DB_DSN
    if (-not $dsn) { Write-Error 'Set DB_DSN env var with your Postgres DSN.'; break }
    python scripts/py/auto_migrate.py --dsn $dsn
  }
  'alembic-draft' {
    if (-not $env:DATABASE_URL) { Write-Error 'Set DATABASE_URL for Alembic (e.g., postgresql://user:pass@host:5432/db)'; break }
    python scripts/py/alembic_draft.py
  }
  'local' {
    # Start DB container only
    if (-not $env:IMPORTS_ENABLED) { $env:IMPORTS_ENABLED = '1' }
    # Imports validation flags (toggle as needed in dev)
    if (-not $env:IMPORTS_VALIDATE_CURRENCY) { $env:IMPORTS_VALIDATE_CURRENCY = 'true' }
    if (-not $env:IMPORTS_REQUIRE_CATEGORIES) { $env:IMPORTS_REQUIRE_CATEGORIES = 'true' }
    if (-not $env:DB_DSN) { $env:DB_DSN = 'postgresql://postgres:root@localhost:5432/gestiqclouddb_dev' }
    docker compose up -d db
    # Ensure backend env defaults
    if (-not $env:FRONTEND_URL) { $env:FRONTEND_URL = 'http://localhost:8081' }
    if (-not $env:DATABASE_URL) { $env:DATABASE_URL = $env:DB_DSN }
    if (-not $env:TENANT_NAMESPACE_UUID) { $env:TENANT_NAMESPACE_UUID = [guid]::NewGuid().ToString() }
    # Apply migrations and check schema
    python scripts/py/auto_migrate.py --dsn $env:DB_DSN
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python scripts/py/check_schema.py --dsn $env:DB_DSN
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    # Run backend locally with hot-reload (ensure PYTHONPATH includes repo and /apps)
    $env:PYTHONPATH = "{0};{1};{2}" -f $PWD, "$PWD/apps", "$PWD/apps/backend"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir "${PWD}/apps/backend"
  }
  'compose-min' {
    # Bring up DB, run migrations service, then backend only
    docker compose up -d db migrations backend
  }
  'compose-backend' {
    # Start only backend (assumes migrations already ran)
    docker compose up -d backend
  }
  'compose-all' {
    # Full stack
    docker compose up -d db migrations backend admin tenant
  }
  default { Write-Host "Usage: scripts/init.ps1 {up|down|rebuild|logs [svc]|typecheck|migrate [up|down] [dir]|schema-check|schema-explain|auto-migrate|alembic-draft|baseline|local|compose-min|compose-backend|compose-all}" }
}

