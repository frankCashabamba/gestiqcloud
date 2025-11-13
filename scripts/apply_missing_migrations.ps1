# ============================================================================
# Script: Aplicar Migraciones Faltantes
# Descripción: Aplica SOLO las migraciones que faltan según schema_migrations
# Autor: GestiQCloud Team
# Fecha: 2025-11-03
# ============================================================================

Write-Host "=== Aplicando migraciones faltantes ===" -ForegroundColor Cyan

# Migraciones pendientes (en orden)
$migrations = @(
    "2025-11-03_200_add_recipe_computed_columns",
    "2025-11-03_200_production_orders",
    "2025-11-03_201_add_unit_conversion",
    "2025-11-03_201_hr_nominas",
    "2025-11-03_202_finance_caja",
    "2025-11-03_203_accounting"
)

foreach ($migration in $migrations) {
    Write-Host "`n[INFO] Aplicando migracion: $migration" -ForegroundColor Yellow
    
    $upFile = "ops\migrations\$migration\up.sql"
    
    if (Test-Path $upFile) {
        # Ejecutar migración
        Get-Content $upFile | docker exec -i db psql -U postgres -d gestiqclouddb_dev
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] $migration aplicada exitosamente" -ForegroundColor Green
            
            # Registrar en schema_migrations
            $name = $migration.Split('_')[-1]
            $insertSql = "INSERT INTO schema_migrations (version, name, status, applied_at) VALUES ('$migration', '$name', 'success', NOW()) ON CONFLICT (version) DO NOTHING;"
            echo $insertSql | docker exec -i db psql -U postgres -d gestiqclouddb_dev
        } else {
            Write-Host "[ERROR] Fallo aplicando $migration" -ForegroundColor Red
            Write-Host "Continuando con siguiente migracion..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARN] Archivo no encontrado: $upFile" -ForegroundColor Magenta
    }
}

Write-Host "`n=== Verificando tablas creadas ===" -ForegroundColor Cyan
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt" | Select-String "nominas|empleados|plan_cuentas|cierres_caja"

Write-Host "`n[OK] Proceso completado" -ForegroundColor Green
Write-Host "[INFO] Ahora puedes reactivar el archivo nomina.py:" -ForegroundColor Yellow
Write-Host "  ren apps\backend\app\models\hr\nomina.py.disabled nomina.py" -ForegroundColor White
Write-Host "  docker compose restart backend" -ForegroundColor White
