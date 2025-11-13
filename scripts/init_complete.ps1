# ============================================================================
# Script: Inicialización Completa GestiQCloud
# Ejecuta TODO en orden correcto: DB → Migraciones → Backend
# ============================================================================

Write-Host "=== GestiQCloud - Inicialización Completa ===" -ForegroundColor Cyan

# 1. Levantar solo DB
Write-Host "`n[1/4] Levantando base de datos..." -ForegroundColor Yellow
docker compose up -d db
Start-Sleep -Seconds 5

# 2. Aplicar migraciones
Write-Host "`n[2/4] Aplicando migraciones pendientes..." -ForegroundColor Yellow
.\scripts\apply_missing_migrations.ps1

# 3. Crear tablas complementarias
Write-Host "`n[3/4] Creando tablas complementarias..." -ForegroundColor Yellow
powershell -Command "Get-Content scripts\fix_all_missing_tables.sql | docker exec -i db psql -U postgres -d gestiqclouddb_dev"
powershell -Command "Get-Content scripts\create_all_missing_complete.sql | docker exec -i db psql -U postgres -d gestiqclouddb_dev"

# 4. Habilitar módulos avanzados
Write-Host "`n[4/4] Habilitando módulos avanzados..." -ForegroundColor Yellow
$env:ENABLE_NOMINAS_MODULE = "true"
$env:ENABLE_PRODUCTION_MODULE = "true"
$env:ENABLE_ACCOUNTING_MODULE = "true"

# 5. Mover modelos a ubicación correcta
Write-Host "`nMoviendo modelos a ubicación activa..." -ForegroundColor Yellow
if (Test-Path 'apps\backend\app\models\hr\_nomina.py') {
    Move-Item 'apps\backend\app\models\hr\_nomina.py' 'apps\backend\app\models\hr\nomina.py' -Force
}
if (Test-Path 'apps\backend\app\models\production\_production_order.py') {
    Move-Item 'apps\backend\app\models\production\_production_order.py' 'apps\backend\app\models\production\production_order.py' -Force
}
if (Test-Path 'apps\backend\app\models\accounting\_plan_cuentas.py') {
    Move-Item 'apps\backend\app\models\accounting\_plan_cuentas.py' 'apps\backend\app\models\accounting\plan_cuentas.py' -Force
}

# 6. Actualizar __init__.py para cargar módulos
$hrInit = @"
"""HR (Human Resources) module models"""
import os

from .empleado import Empleado, Vacacion
from .nomina import Nomina, NominaConcepto, NominaPlantilla

__all__ = ["Empleado", "Vacacion", "Nomina", "NominaConcepto", "NominaPlantilla"]
"@
Set-Content -Path 'apps\backend\app\models\hr\__init__.py' -Value $hrInit

$prodInit = @"
"""Production models"""
from app.models.production.production_order import ProductionOrder, ProductionOrderLine

__all__ = ["ProductionOrder", "ProductionOrderLine"]
"@
Set-Content -Path 'apps\backend\app\models\production\__init__.py' -Value $prodInit

$accInit = @"
"""Accounting models"""
from app.models.accounting.plan_cuentas import PlanCuentas, AsientoContable, AsientoLinea

__all__ = ["PlanCuentas", "AsientoContable", "AsientoLinea"]
"@
Set-Content -Path 'apps\backend\app\models\accounting\__init__.py' -Value $accInit

# 7. Levantar resto del stack
Write-Host "`n[OK] Levantando stack completo..." -ForegroundColor Green
docker compose up -d

Write-Host "`n=== Inicializacion completada ===" -ForegroundColor Cyan
Write-Host "[OK] DB: Listo" -ForegroundColor Green
Write-Host "[OK] Migraciones: Listo" -ForegroundColor Green
Write-Host "[OK] Backend: Listo" -ForegroundColor Green
Write-Host "`nAccede a:" -ForegroundColor Yellow
Write-Host "  Admin: http://localhost:8081" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
