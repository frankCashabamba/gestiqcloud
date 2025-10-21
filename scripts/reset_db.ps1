Param(
  [string]$DbName = "gestiqclouddb_dev",
  [string]$Service = "db",
  [string]$User = "postgres",
  [string]$Password = "root",
  [int]$Port = 5432,
  [switch]$ApplyMigrations = $true,
  [switch]$DropSchemaOnly = $true    # Drop schema inside DB to avoid orphaned objects
)

Write-Host "[reset-db] Ensuring Postgres service is up..."
try {
  docker compose up -d $Service | Out-Null
} catch {
  Write-Warning "docker compose not available or failed. Ensure Docker Desktop is running."
}

if (-not $DropSchemaOnly) {
  Write-Host "[reset-db] Dropping and recreating database '$DbName' in service '$Service'..."
  try {
    # Terminate active connections
    docker compose exec -T $Service psql -U $User -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DbName' AND pid <> pg_backend_pid();" | Out-Null
    # Drop database
    docker compose exec -T $Service psql -U $User -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DbName;" | Out-Null
    # Create database
    docker compose exec -T $Service psql -U $User -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DbName;" | Out-Null
    Write-Host "[reset-db] Database recreated."
  } catch {
    Write-Error "[reset-db] Failed to reset database: $($_.Exception.Message)"
    exit 1
  }
}

# Always drop and recreate schema 'public' to avoid orphans (sequences, triggers, policies)
Write-Host "[reset-db] Dropping schema 'public' and recreating (extensions, grants)..."
try {
  $ddl = @(
    'DROP SCHEMA IF EXISTS public CASCADE;',
    'CREATE SCHEMA public;',
    'GRANT ALL ON SCHEMA public TO postgres;',
    'GRANT ALL ON SCHEMA public TO public;',
    'CREATE EXTENSION IF NOT EXISTS pgcrypto;',
    'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
  ) -join ' '
  docker compose exec -T $Service psql -U $User -d $DbName -v ON_ERROR_STOP=1 -c "$ddl" | Out-Null
  Write-Host "[reset-db] Schema recreated and extensions ensured."
} catch {
  Write-Error "[reset-db] Failed to recreate schema: $($_.Exception.Message)"
  exit 1
}

if ($ApplyMigrations) {
  Write-Host "[reset-db] Applying migrations inside compose (service 'migrations')..."
  try {
    # Run migrations job referencing the DB by service hostname 'db'
    docker compose --profile migrate run --rm -e DB_DSN="postgresql://$User`:$Password@${Service}:$Port/$DbName" migrations
    if ($LASTEXITCODE -ne 0) { throw "auto_migrate returned code $LASTEXITCODE" }
    Write-Host "[reset-db] Migrations applied successfully (compose job)."
  } catch {
    Write-Warning "[reset-db] Compose migrations job failed: $($_.Exception.Message)"
    Write-Host "[reset-db] Falling back to host Python auto_migrate with localhost DSN..."
    $dsn = "postgresql://${User}:${Password}@localhost:${Port}/${DbName}"
    $env:DB_DSN = $dsn
    & python "scripts/py/auto_migrate.py" --dir "ops/migrations"
    if ($LASTEXITCODE -ne 0) {
      Write-Error "[reset-db] Migrations failed with exit code $LASTEXITCODE."
      exit $LASTEXITCODE
    }
    Write-Host "[reset-db] Migrations applied successfully (host fallback)."
  }
}

Write-Host "[reset-db] Done."
