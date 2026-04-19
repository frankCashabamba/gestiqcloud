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

Set-Location $backendPath

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; celery -A celery_app worker -l info -Q critical,notifications,einvoicing -c 2 -n worker_critical@%h"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; celery -A celery_app worker -l info -Q default -c 2 -n worker_default@%h"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; celery -A celery_app worker -l info -Q importador_fast,importador_deep -c 2 -n worker_ai@%h"
