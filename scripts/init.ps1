param(
  [Parameter(Position=0)][string]$cmd = "help",
  [Parameter(Position=1)][string]$arg1 = "backend",
  [Parameter(Position=2)][string]$arg2 = ""
)

function Set-DevEnvDefaults {
  if (-not $env:IMPORTS_ENABLED) { $env:IMPORTS_ENABLED = '1' }
  if (-not $env:RUN_MIGRATIONS) { $env:RUN_MIGRATIONS = '1' }
  if (-not $env:DB_DSN) { $env:DB_DSN = 'postgresql://postgres:root@localhost:5432/gestiqclouddb_dev' }
  if (-not $env:FRONTEND_URL) { $env:FRONTEND_URL = 'http://localhost:8081' }
  if (-not $env:DATABASE_URL) { $env:DATABASE_URL = $env:DB_DSN }
  if (-not $env:TENANT_NAMESPACE_UUID) { $env:TENANT_NAMESPACE_UUID = [guid]::NewGuid().ToString() }
}

switch ($cmd) {
  'up' { Set-DevEnvDefaults; docker compose up -d --build }
  'up-dev' { Set-DevEnvDefaults; docker compose up --build }
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
  'migrate-local' {
    # Run hardened bootstrap (statement-by-statement) against ops/migrations
    $dsn = $env:DB_DSN
    if (-not $dsn) { Write-Error 'Set DB_DSN env var with your Postgres DSN.'; break }
    python scripts/py/auto_migrate.py --dsn $dsn --dir ops/migrations
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  'alembic-draft' {
    if (-not $env:DATABASE_URL) { Write-Error 'Set DATABASE_URL for Alembic (e.g., postgresql://user:pass@host:5432/db)'; break }
    python scripts/py/alembic_draft.py
  }
  'alembic-upgrade' {
    # Optional: run Alembic upgrade (use only if Alembic is the desired source of truth)
    if (-not $env:DATABASE_URL) { Write-Error 'Set DATABASE_URL (postgresql://user:pass@host:5432/db)'; break }
    pushd apps/backend
    alembic upgrade head
    $code = $LASTEXITCODE
    popd
    if ($code -ne 0) { exit $code }
  }
  'local' {
    # Start DB container only
    Set-DevEnvDefaults
    # Imports validation flags (toggle as needed in dev)
    if (-not $env:IMPORTS_VALIDATE_CURRENCY) { $env:IMPORTS_VALIDATE_CURRENCY = 'true' }
    if (-not $env:IMPORTS_REQUIRE_CATEGORIES) { $env:IMPORTS_REQUIRE_CATEGORIES = 'true' }
    docker compose up -d db
    # Ensure backend env defaults
    # Apply migrations and check schema
    python scripts/py/auto_migrate.py --dsn $env:DB_DSN --dir ops/migrations
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python scripts/py/check_schema.py --dsn $env:DB_DSN
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    # Run backend locally with hot-reload (ensure PYTHONPATH includes repo and /apps)
    $env:PYTHONPATH = "{0};{1};{2}" -f $PWD, "$PWD/apps", "$PWD/apps/backend"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir "${PWD}/apps/backend"
  }
  'compose-min' {
    # Bring up DB, run migrations service, then backend only
    Set-DevEnvDefaults
    docker compose up -d db migrations backend
  }
  'compose-backend' {
    # Start only backend (assumes migrations already ran)
    Set-DevEnvDefaults
    docker compose up -d backend
  }
  'compose-web' {
    # Start admin + tenant using the 'web' profile
    Set-DevEnvDefaults
    docker compose --profile web up -d admin tenant
  }
  'compose-worker' {
    # Start redis + celery worker using the 'worker' profile
    Set-DevEnvDefaults
    docker compose --profile worker up -d redis celery-worker
  }
  'compose-migrate' {
    # Run migrations one-off (honors RUN_MIGRATIONS)
    Set-DevEnvDefaults
    docker compose --profile migrate run --rm -e DB_DSN=postgresql://postgres:root@db:5432/gestiqclouddb_dev migrations
  }
  'compose-no-migrations' {
    # Start stack without migrations service (use with migrate-local or Render job)
    Set-DevEnvDefaults
    docker compose up -d db backend admin tenant
  }
  'up-all' {
    # Bring up full local stack in order: db -> migrations -> backend -> web -> worker
    Set-DevEnvDefaults
    Write-Host "[1/6] Starting DB..."
    docker compose up -d db
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[2/6] Rebuilding images (no-cache): backend, admin, tenant, migrations..."
    docker compose build --no-cache backend admin tenant migrations
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $runMigs = $env:RUN_MIGRATIONS
    if ($runMigs -and ($runMigs -in @('1','true','True','TRUE'))) {
      Write-Host "[3/6] Running migrations (one-off)..."
      docker compose --profile migrate run --rm -e DB_DSN=postgresql://postgres:root@db:5432/gestiqclouddb_dev migrations
      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
      Write-Host "[3/6] Skipping migrations (RUN_MIGRATIONS=0)"
    }
    Write-Host "[4/6] Starting backend..."
    docker compose up -d --build backend
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[5/6] Starting web (admin + tenant)..."
    docker compose --profile web up -d --build admin tenant
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[6/6] Starting worker (redis + celery)..."
    docker compose --profile worker up -d redis celery-worker
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Full stack is up: backend:8000, admin:8081, tenant:8082"
  }
  'render-migrate' {
    # Trigger Render job if configured (optional)
    if (-not $env:RENDER_MIGRATE_JOB_ID) { Write-Error 'Set RENDER_MIGRATE_JOB_ID'; break }
    if (-not $env:RENDER_API_TOKEN) { Write-Error 'Set RENDER_API_TOKEN'; break }
    $jobId = $env:RENDER_MIGRATE_JOB_ID
    $url = "https://api.render.com/v1/jobs/$jobId/runs"
    try {
      $resp = Invoke-RestMethod -Method Post -Uri $url -Headers @{ Authorization = "Bearer $($env:RENDER_API_TOKEN)" } -ContentType 'application/json' -Body '{}'
      Write-Host "Render migrate job triggered: $($resp.id) status=$($resp.status)"
    } catch {
      Write-Error "Failed to trigger Render job: $($_.Exception.Message)"
      exit 1
    }
  }
  'compose-all' {
    # Full stack
    Set-DevEnvDefaults
    docker compose up -d db migrations backend admin tenant
  }
  'seed-admin' {
    # Create/update global SuperUser for Admin panel (local/dev)
    # Usage: scripts/init.ps1 seed-admin [password]
    # Env overrides: ADMIN_USER, ADMIN_EMAIL, ADMIN_PASS
    Set-DevEnvDefaults
    $user = if ($env:ADMIN_USER) { $env:ADMIN_USER } else { 'admin' }
    $email = if ($env:ADMIN_EMAIL) { $env:ADMIN_EMAIL } else { 'admin@local' }
    $pass = if ($arg1) { $arg1 } elseif ($env:ADMIN_PASS) { $env:ADMIN_PASS } else { 'Admin.2025' }
    if (-not $env:DATABASE_URL -and $env:DB_DSN) { $env:DATABASE_URL = $env:DB_DSN }
    Write-Host "Seeding SuperUser → username=$user email=$email"
    # Prefer running inside backend container to guarantee same DB (host=db)
    $ranInContainer = $false
    try {
      docker compose ps backend | Out-Null
      if ($LASTEXITCODE -eq 0) {
        docker compose exec backend python /scripts/py/create_superuser.py --username $user --email $email --password $pass
        if ($LASTEXITCODE -eq 0) { $ranInContainer = $true }
        else { Write-Error "Seeding inside container failed (see above). Not falling back to host to avoid wrong DB."; exit $LASTEXITCODE }
      }
    } catch {
      # if docker compose not available, fallback to host
    }
    if (-not $ranInContainer) {
      python scripts/py/create_superuser.py --username $user --email $email --password $pass
      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
  }
  default { Write-Host "Usage: scripts/init.ps1 {up|down|rebuild|logs [svc]|typecheck|migrate [up|down] [dir]|schema-check|schema-explain|auto-migrate|migrate-local|alembic-draft|alembic-upgrade|baseline|local|compose-min|compose-backend|compose-no-migrations|compose-web|compose-worker|compose-migrate|compose-all|up-all|render-migrate}" }
}

