Write-Host "=== GestiQCloud Workers Local ===" -ForegroundColor Cyan

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendPath = Join-Path $repoRoot "apps/backend"
$venvActivate = Join-Path $repoRoot ".venv/Scripts/Activate.ps1"

if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Host "No se encontro .venv." -ForegroundColor Red
    exit 1
}

# Cargar variables desde .env raiz (igual que start_local.ps1)
$rootEnvPath = Join-Path $repoRoot ".env"
if (-not (Test-Path $rootEnvPath)) {
    Write-Host "No se encontro .env en la raiz del repo." -ForegroundColor Red
    exit 1
}
$envLines = Get-Content $rootEnvPath
function Get-EnvVal([string[]]$lines, [string]$key, [string]$default = "") {
    $match = $lines | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
    if (-not $match) { return $default }
    return ($match.Split("=", 2)[1]).Trim().Trim('"').Trim("'")
}

$redisUrl     = Get-EnvVal $envLines "REDIS_URL" "redis://127.0.0.1:6379/1"
$databaseUrl  = Get-EnvVal $envLines "DATABASE_URL"
$dbDsn        = Get-EnvVal $envLines "DB_DSN" $databaseUrl

if (-not $databaseUrl) {
    Write-Host "DATABASE_URL no definido en .env" -ForegroundColor Red
    exit 1
}

Write-Host "REDIS_URL=$redisUrl" -ForegroundColor Gray
Write-Host "DATABASE_URL=<cargado desde .env>" -ForegroundColor Gray

$envBlock = "`$env:REDIS_URL='$redisUrl'; `$env:DATABASE_URL='$databaseUrl'; `$env:DB_DSN='$dbDsn'; `$env:ENV_FILE='$rootEnvPath'"

Set-Location $backendPath

# --pool=solo requerido en Windows (prefork usa semaforos que Windows no permite)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$envBlock; cd '$backendPath'; celery -A celery_app worker -l info -Q critical,notifications,einvoicing --pool=solo -n worker_critical@%h"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$envBlock; cd '$backendPath'; celery -A celery_app worker -l info -Q default --pool=solo -n worker_default@%h"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$envBlock; cd '$backendPath'; celery -A app.config.celery_config worker -l info -Q importador_fast --pool=solo -n worker_importador_fast@%h"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$envBlock; cd '$backendPath'; celery -A app.config.celery_config worker -l info -Q importador_deep --pool=solo -n worker_importador_deep@%h"
