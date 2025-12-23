# Script para limpiar caché de Vite completamente
Write-Host "🧹 Limpiando caché de Vite..." -ForegroundColor Cyan

# 1. Matar procesos node
Write-Host "[1/5] Deteniendo procesos Node..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Limpiar dist y vite cache
Write-Host "[2/5] Removiendo dist y .vite..." -ForegroundColor Yellow
Remove-Item -Recurse -Force apps/admin/dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force apps/admin/.vite -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force apps/tenant/dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force apps/tenant/.vite -ErrorAction SilentlyContinue

# 3. Limpiar node_modules/.vite
Write-Host "[3/5] Removiendo node_modules/.vite..." -ForegroundColor Yellow
Remove-Item -Recurse -Force apps/admin/node_modules/.vite -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force apps/tenant/node_modules/.vite -ErrorAction SilentlyContinue

# 4. Limpiar .env de apps (para forzar reinit)
Write-Host "[4/5] Removiendo .env locales..." -ForegroundColor Yellow
Remove-Item -Path apps/admin/.env -Force -ErrorAction SilentlyContinue
Remove-Item -Path apps/tenant/.env -Force -ErrorAction SilentlyContinue

# 5. Mostrar verificación
Write-Host "[5/5] Verificando limpiezas..." -ForegroundColor Yellow
if (Test-Path apps/admin/dist) {
    Write-Host "⚠️  dist aún existe" -ForegroundColor Red
} else {
    Write-Host "✅ dist removido" -ForegroundColor Green
}

if (Test-Path apps/admin/.vite) {
    Write-Host "⚠️  .vite aún existe" -ForegroundColor Red
} else {
    Write-Host "✅ .vite removido" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Caché completamente limpiado" -ForegroundColor Green
Write-Host ""
Write-Host "Próxima acción:" -ForegroundColor Cyan
Write-Host "1. Abre browser en incognito (Ctrl+Shift+N)" -ForegroundColor White
Write-Host "2. Ejecuta: scripts/start_local.ps1" -ForegroundColor White
Write-Host "3. Navega a: http://localhost:8081/admin" -ForegroundColor White
Write-Host "4. Login normalmente" -ForegroundColor White
