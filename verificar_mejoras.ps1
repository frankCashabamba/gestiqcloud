# Script de verificacion de mejoras (PowerShell)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VERIFICACION DE MEJORAS IMPLEMENTADAS" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$ChecksPassed = 0
$ChecksFailed = 0
$ChecksWarning = 0

function Check-File {
    param($Path)
    if (Test-Path $Path) {
        Write-Host "OK - Archivo existe: $Path" -ForegroundColor Green
        $script:ChecksPassed++
    } else {
        Write-Host "FAIL - Archivo falta: $Path" -ForegroundColor Red
        $script:ChecksFailed++
    }
}

function Check-Content {
    param($Path, $Pattern, $Description)
    if (Test-Path $Path) {
        $content = Get-Content $Path -Raw -ErrorAction SilentlyContinue
        if ($content -match $Pattern) {
            Write-Host "OK - Configurado: $Description" -ForegroundColor Green
            $script:ChecksPassed++
        } else {
            Write-Host "WARN - Falta: $Description" -ForegroundColor Yellow
            $script:ChecksWarning++
        }
    }
}

Write-Host "1. Verificando archivos creados..." -ForegroundColor White
Write-Host ""

Check-File "apps\backend\pyproject.toml"
Check-File "apps\backend\requirements-dev.txt"
Check-File "apps\backend\app\core\auth_cookies.py"
Check-File "apps\backend\app\middleware\endpoint_rate_limit.py"
Check-File "apps\backend\app\tests\test_auth_cookies.py"
Check-File "apps\tenant\.eslintrc.json"
Check-File "apps\admin\.eslintrc.json"
Check-File ".github\dependabot.yml"

Write-Host ""
Write-Host "2. Verificando configuraciones..." -ForegroundColor White
Write-Host ""

Check-Content ".pre-commit-config.yaml" "mypy" "Pre-commit: mypy"
Check-Content ".pre-commit-config.yaml" "bandit" "Pre-commit: bandit"
Check-Content "apps\backend\app\main.py" "EndpointRateLimiter" "Rate limiting"
Check-Content "apps\tenant\package.json" '"lint"' "NPM lint (tenant)"
Check-Content "apps\tenant\vite.config.ts" "manualChunks" "Code splitting"

Write-Host ""
Write-Host "3. Verificando documentacion..." -ForegroundColor White
Write-Host ""

Check-File "Informe_Backend.md"
Check-File "Informe_Frontend.md"
Check-File "RESUMEN_AUDITORIA.md"
Check-File "TAREAS_COMPLETADAS.md"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Checks pasados: $ChecksPassed" -ForegroundColor Green
Write-Host "Warnings: $ChecksWarning" -ForegroundColor Yellow
Write-Host "Checks fallidos: $ChecksFailed" -ForegroundColor Red
Write-Host ""

if ($ChecksFailed -eq 0) {
    Write-Host "VERIFICACION EXITOSA" -ForegroundColor Green
    Write-Host ""
    Write-Host "Proximos pasos:" -ForegroundColor Cyan
    Write-Host "1. cd apps\backend; pip install -r requirements-dev.txt"
    Write-Host "2. cd apps\tenant; npm install --save-dev eslint ..."
    Write-Host "3. Ver INSTRUCCIONES_MEJORAS.md para detalles"
    exit 0
} else {
    Write-Host "HAY VERIFICACIONES FALLIDAS" -ForegroundColor Red
    exit 1
}
