# Modernización masiva Backend → Inglés
# Ejecuta desde: C:\Users\pc_cashabamba\Documents\GitHub\proyecto

Write-Host "=== MODERNIZACIÓN BACKEND A INGLÉS ===" -ForegroundColor Cyan

$baseDir = "apps\backend\app"

# 1) Dotted attributes en TODOS los .py
Write-Host "`n1. Actualizando dotted attributes..." -ForegroundColor Yellow
$allPyFiles = Get-ChildItem $baseDir -Recurse -Filter *.py
$count = 0
foreach ($f in $allPyFiles) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $original = $content

    $content = $content -replace '\.nombre\b', '.name'
    $content = $content -replace '\.descripcion\b', '.description'
    $content = $content -replace '\.precio\b', '.price'
    $content = $content -replace '\.activo\b', '.active'
    $content = $content -replace '\.ruc\b', '.tax_id'
    $content = $content -replace '\.telefono\b', '.phone'
    $content = $content -replace '\.direccion\b', '.address'
    $content = $content -replace '\.ciudad\b', '.city'
    $content = $content -replace '\.provincia\b', '.state'

    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($f.FullName, $content, [System.Text.Encoding]::UTF8)
        $count++
    }
}
Write-Host "  → $count archivos actualizados" -ForegroundColor Green

# 2) Schemas Pydantic - Nombres de campos
Write-Host "`n2. Actualizando schemas Pydantic..." -ForegroundColor Yellow
$schemaFiles = @()
$schemaFiles += Get-ChildItem "apps\backend\app\schemas" -Filter *.py
$schemaFiles += Get-ChildItem "apps\backend\app\modules" -Recurse -Filter schemas.py

$countSchemas = 0
foreach ($f in $schemaFiles) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $original = $content

    # Reemplazar nombres de campo (palabra completa)
    $content = $content -replace '\bnombre:', 'name:'
    $content = $content -replace '\bdescripcion:', 'description:'
    $content = $content -replace '\bprecio:', 'price:'
    $content = $content -replace '\bactivo:', 'active:'
    $content = $content -replace '\bruc:', 'tax_id:'
    $content = $content -replace '\btelefono:', 'phone:'
    $content = $content -replace '\bdireccion:', 'address:'
    $content = $content -replace '\bciudad:', 'city:'
    $content = $content -replace '\bprovincia:', 'state:'

    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($f.FullName, $content, [System.Text.Encoding]::UTF8)
        $countSchemas++
    }
}
Write-Host "  → $countSchemas schemas actualizados" -ForegroundColor Green

# 3) codigo → sku SOLO en productos
Write-Host "`n3. Actualizando codigo → sku en productos..." -ForegroundColor Yellow
$productFiles = Get-ChildItem $baseDir -Recurse -Filter *.py | Where-Object {
    $_.FullName -match 'products|productos'
}

$countProducts = 0
foreach ($f in $productFiles) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $original = $content

    $content = $content -replace '\.codigo\b', '.sku'
    $content = $content -replace '\bcodigo:', 'sku:'

    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($f.FullName, $content, [System.Text.Encoding]::UTF8)
        $countProducts++
    }
}
Write-Host "  → $countProducts archivos de productos actualizados" -ForegroundColor Green

Write-Host "`n=== MODERNIZACIÓN COMPLETA ===" -ForegroundColor Cyan
Write-Host "Total archivos actualizados: $($count + $countSchemas + $countProducts)" -ForegroundColor Green
Write-Host "`nReinicia el backend: docker restart backend" -ForegroundColor Yellow
