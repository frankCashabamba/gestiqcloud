<#
.SYNOPSIS
  Crea/actualiza el rol de aplicacion gestiq_app (NO-superuser) leyendo la
  contraseña y el nombre de BD desde el .env. Ver 01_create_app_role.sql.

.DESCRIPTION
  - Conexion superuser: variable SUPERUSER_URL del .env si existe, si no DATABASE_URL.
  - Contraseña del rol: APP_DB_PASSWORD del .env (obligatoria).
  - Nombre de BD: se extrae de la URL de conexion.
  Requiere psql en el PATH.

.EXAMPLE
  ops/security/apply_app_role.ps1
  ops/security/apply_app_role.ps1 -EnvFile .env.production
#>
param(
  [string]$EnvFile = (Join-Path $PSScriptRoot "..\..\.env"),
  [string]$SqlFile = (Join-Path $PSScriptRoot "01_create_app_role.sql")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) { throw "No existe el .env: $EnvFile" }
if (-not (Test-Path $SqlFile)) { throw "No existe el SQL: $SqlFile" }

# --- Parsear .env (KEY=VALUE, ignora comentarios y vacias) ---
$envMap = @{}
foreach ($line in Get-Content $EnvFile) {
  $t = $line.Trim()
  if ($t -eq "" -or $t.StartsWith("#")) { continue }
  $idx = $t.IndexOf("=")
  if ($idx -lt 1) { continue }
  $key = $t.Substring(0, $idx).Trim()
  $val = $t.Substring($idx + 1).Trim().Trim('"').Trim("'")
  $envMap[$key] = $val
}

$superUrl = $envMap["SUPERUSER_URL"]
if (-not $superUrl) { $superUrl = $envMap["DATABASE_URL"] }
if (-not $superUrl) { throw "No hay SUPERUSER_URL ni DATABASE_URL en $EnvFile" }

$appPw = $envMap["APP_DB_PASSWORD"]
if (-not $appPw) { throw "Falta APP_DB_PASSWORD en $EnvFile" }

# --- Extraer nombre de BD de la URL: ...://user:pass@host:port/DBNAME?params ---
$dbname = ($superUrl -replace '^.*/', '') -replace '\?.*$', ''
if (-not $dbname) { throw "No se pudo extraer el nombre de BD de la URL de conexion" }

Write-Host "Aplicando rol gestiq_app sobre BD '$dbname' (conexion superuser)..." -ForegroundColor Cyan

$pwArg = "app_pw='$appPw'"
$dbArg = "dbname=$dbname"

& psql $superUrl -v $pwArg -v $dbArg -f $SqlFile
if ($LASTEXITCODE -ne 0) { throw "psql fallo con codigo $LASTEXITCODE" }

Write-Host "Rol gestiq_app listo. Verifica con:" -ForegroundColor Green
Write-Host "  psql `"$superUrl`" -c `"SELECT rolsuper, rolbypassrls, rolcreatedb FROM pg_roles WHERE rolname='gestiq_app';`""
Write-Host "Luego cambia DATABASE_URL/DB_DSN (backend Y workers) al rol gestiq_app." -ForegroundColor Yellow
