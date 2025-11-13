# Modernización masiva Frontend → Inglés
# Actualiza Admin + Tenant

Write-Host "=== MODERNIZACIÓN FRONTEND A INGLÉS ===" -ForegroundColor Cyan

# 1) Tenant
Write-Host "`n1. Actualizando Frontend Tenant..." -ForegroundColor Yellow
$tenantFiles = Get-ChildItem "apps\tenant\src" -Recurse -Include *.ts,*.tsx
$countTenant = 0

foreach ($f in $tenantFiles) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $original = $content
    
    # Dotted attributes
    $content = $content -replace '\.nombre\b', '.name'
    $content = $content -replace '\.descripcion\b', '.description'
    $content = $content -replace '\.codigo\b', '.sku'
    $content = $content -replace '\.precio\b', '.price'
    $content = $content -replace '\.activo\b', '.active'
    $content = $content -replace '\.ruc\b', '.tax_id'
    $content = $content -replace '\.telefono\b', '.phone'
    $content = $content -replace '\.direccion\b', '.address'
    $content = $content -replace '\.ciudad\b', '.city'
    $content = $content -replace '\.provincia\b', '.state'
    $content = $content -replace '\.ubicacion\b', '.location'
    $content = $content -replace '\.lote\b', '.lot'
    
    # Type properties
    $content = $content -replace '\bnombre:', 'name:'
    $content = $content -replace '\bdescripcion:', 'description:'
    $content = $content -replace '\bcodigo:', 'sku:'
    $content = $content -replace '\bprecio:', 'price:'
    $content = $content -replace '\bactivo:', 'active:'
    $content = $content -replace '\bruc:', 'tax_id:'
    $content = $content -replace '\btelefono:', 'phone:'
    $content = $content -replace '\bdireccion:', 'address:'
    $content = $content -replace '\bciudad:', 'city:'
    $content = $content -replace '\bprovincia:', 'state:'
    $content = $content -replace '\bubicacion:', 'location:'
    $content = $content -replace '\blote:', 'lot:'
    
    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($f.FullName, $content, [System.Text.Encoding]::UTF8)
        $countTenant++
    }
}
Write-Host "  → Tenant: $countTenant archivos actualizados" -ForegroundColor Green

# 2) Admin
Write-Host "`n2. Actualizando Frontend Admin..." -ForegroundColor Yellow
$adminFiles = Get-ChildItem "apps\admin\src" -Recurse -Include *.ts,*.tsx
$countAdmin = 0

foreach ($f in $adminFiles) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $original = $content
    
    # Dotted attributes
    $content = $content -replace '\.nombre\b', '.name'
    $content = $content -replace '\.descripcion\b', '.description'
    $content = $content -replace '\.codigo\b', '.sku'
    $content = $content -replace '\.precio\b', '.price'
    $content = $content -replace '\.activo\b', '.active'
    $content = $content -replace '\.ruc\b', '.tax_id'
    $content = $content -replace '\.telefono\b', '.phone'
    $content = $content -replace '\.direccion\b', '.address'
    $content = $content -replace '\.ciudad\b', '.city'
    $content = $content -replace '\.provincia\b', '.state'
    
    # Type properties
    $content = $content -replace '\bnombre:', 'name:'
    $content = $content -replace '\bdescripcion:', 'description:'
    $content = $content -replace '\bcodigo:', 'sku:'
    $content = $content -replace '\bprecio:', 'price:'
    $content = $content -replace '\bactivo:', 'active:'
    $content = $content -replace '\bruc:', 'tax_id:'
    $content = $content -replace '\btelefono:', 'phone:'
    $content = $content -replace '\bdireccion:', 'address:'
    $content = $content -replace '\bciudad:', 'city:'
    $content = $content -replace '\bprovincia:', 'state:'
    
    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($f.FullName, $content, [System.Text.Encoding]::UTF8)
        $countAdmin++
    }
}
Write-Host "  → Admin: $countAdmin archivos actualizados" -ForegroundColor Green

Write-Host "`n=== MODERNIZACIÓN FRONTEND COMPLETA ===" -ForegroundColor Cyan
Write-Host "Total: $($countTenant + $countAdmin) archivos actualizados" -ForegroundColor Green
Write-Host "`nReconstruye los contenedores:" -ForegroundColor Yellow
Write-Host "  docker compose build tenant admin" -ForegroundColor White
Write-Host "  docker compose up -d tenant admin" -ForegroundColor White
