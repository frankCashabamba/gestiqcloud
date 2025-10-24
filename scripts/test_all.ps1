# PowerShell Script: Ejecutar todos los tests
# Uso: .\scripts\test_all.ps1

Write-Host "================================================" -ForegroundColor Blue
Write-Host "🧪 GestiQCloud - Test Suite Completo" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Backend Tests
Write-Host "📦 Backend Tests (pytest)" -ForegroundColor Cyan
Write-Host "----------------------------------------"
Set-Location apps\backend
$env:PYTHONPATH = "$PWD;$PWD\apps"
pytest -v `
  app\tests\test_pos_complete.py `
  app\tests\test_spec1_endpoints.py `
  app\tests\test_einvoicing.py `
  app\tests\test_integration_excel_erp.py

Set-Location ..\..
Write-Host ""

# TPV Tests
Write-Host "🏪 TPV Tests (vitest)" -ForegroundColor Cyan
Write-Host "----------------------------------------"
Set-Location apps\tpv
npm test -- --run

Set-Location ..\..
Write-Host ""

# Summary
Write-Host "================================================" -ForegroundColor Green
Write-Host "✅ Test Suite Completado" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:"
Write-Host "1. Revisar coverage: apps\backend\htmlcov\index.html"
Write-Host "2. Tests E2E: Ejecutar manualmente"
Write-Host ""
