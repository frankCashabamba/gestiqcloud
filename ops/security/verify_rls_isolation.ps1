<#
.SYNOPSIS
  Ejecuta la verificacion de aislamiento RLS (verify_rls_isolation.sql) como el rol
  de aplicacion (gestiq_app) leyendo DATABASE_URL del .env.

.DESCRIPTION
  - Localiza psql (PATH o C:\Program Files\PostgreSQL\*\bin).
  - Usa DATABASE_URL del .env (debe apuntar al rol de app NO-superuser).
  - Skip (exit 0) si no hay psql o si la URL no es PostgreSQL (p.ej. SQLite en tests).
  - FALLA (exit 1) si la conexion es superuser o si hay fuga cross-tenant.

  Pensado para engancharse en scripts/local_ci.ps1 y en CI.
#>
param(
  [string]$EnvFile = (Join-Path $PSScriptRoot "..\..\.env"),
  [string]$SqlFile = (Join-Path $PSScriptRoot "verify_rls_isolation.sql")
)

$ErrorActionPreference = "Stop"

# 1) Localizar psql
$psql = (Get-Command psql -ErrorAction SilentlyContinue).Source
if (-not $psql) {
  $cand = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
  if ($cand) { $psql = $cand.FullName }
}
if (-not $psql) {
  Write-Host "SKIP verificacion RLS: psql no encontrado en PATH ni en Program Files." -ForegroundColor DarkYellow
  exit 0
}

# 2) Leer DATABASE_URL del .env (debe ser el rol gestiq_app)
if (-not (Test-Path $EnvFile)) {
  Write-Host "SKIP verificacion RLS: no existe $EnvFile" -ForegroundColor DarkYellow
  exit 0
}
$dbUrl = $null
foreach ($line in Get-Content $EnvFile) {
  $t = $line.Trim()
  if ($t -like "DATABASE_URL=*" -and -not $t.StartsWith("#")) {
    $dbUrl = $t.Substring("DATABASE_URL=".Length).Trim().Trim('"').Trim("'")
    break
  }
}
if (-not $dbUrl) {
  Write-Host "SKIP verificacion RLS: DATABASE_URL no definido en $EnvFile" -ForegroundColor DarkYellow
  exit 0
}
if ($dbUrl -notmatch '^postgres') {
  Write-Host "SKIP verificacion RLS: DATABASE_URL no es PostgreSQL ($dbUrl)." -ForegroundColor DarkYellow
  exit 0
}

Write-Host "Verificando aislamiento RLS como rol de la app..." -ForegroundColor Cyan
& $psql $dbUrl -v ON_ERROR_STOP=1 -f $SqlFile
$code = $LASTEXITCODE
if ($code -ne 0) {
  Write-Host "FALLO verificacion RLS (exit $code) - revisar aislamiento / rol no-superuser." -ForegroundColor Red
}
exit $code
