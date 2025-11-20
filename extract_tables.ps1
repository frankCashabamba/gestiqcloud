# Script para extraer todas las tablas de las migraciones SQL

$migPath = 'C:\Users\pc_cashabamba\Documents\GitHub\proyecto\ops\migrations'
$tables = @{}

Write-Host "Buscando CREATE TABLE en migraciones..." -ForegroundColor Cyan

Get-ChildItem $migPath -Recurse -Filter 'up.sql' | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $folder = $_.Directory.Name

    # Buscar CREATE TABLE
    [regex]::Matches($content, 'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)', 'IgnoreCase') | ForEach-Object {
        $tableName = $_.Groups[1].Value
        if (-not $tables[$tableName]) {
            $tables[$tableName] = $folder
        }
    }
}

# Mostrar resultado
Write-Host "`n=== TABLAS EN MIGRACIONES ===" -ForegroundColor Yellow
Write-Host "Tablas en ESPAÑOL:" -ForegroundColor Red
$spanishTables = $tables.Keys | Where-Object {
    $_ -match '(^[a-z_]*[áéíóúñü]|empleado|vacacion|nomina|caja|banco|movimiento|linea|panaderia|taller|factura|proveedor|venta|compra|gasto|cuenta|asiento|plan)' -and $_ -notmatch '^auth_' -and $_ -notmatch '^alembic'
}

if ($spanishTables) {
    $spanishTables | Sort-Object | ForEach-Object {
        Write-Host "  ❌ $_  (en: $($tables[$_]))" -ForegroundColor Red
    }
} else {
    Write-Host "  ✅ No encontradas con caracteres españoles detectados" -ForegroundColor Green
}

Write-Host "`nTablas en INGLÉS:" -ForegroundColor Green
$englishTables = $tables.Keys | Where-Object {
    $_ -notmatch '(^[a-z_]*[áéíóúñü]|empleado|vacacion|nomina|caja|banco|movimiento|linea|panaderia|taller|factura|proveedor|venta|compra|gasto|cuenta|asiento|plan)'
}

$englishTables | Sort-Object | ForEach-Object {
    Write-Host "  ✅ $_"
}

Write-Host "`n=== RESUMEN ===" -ForegroundColor Yellow
Write-Host "Total tablas: $($tables.Count)"
Write-Host "En español: $($spanishTables | Measure-Object).Count"
Write-Host "En inglés: $($englishTables | Measure-Object).Count"
