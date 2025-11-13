Write-Host "=== GestiQCloud - Inicio Local (sin Docker, como en PRO) ===" -ForegroundColor Cyan

Write-Host "[1/6] Preparando .env..." -ForegroundColor Yellow
$rootEnvPath = ".env.local"
if (Test-Path $rootEnvPath) {
    Copy-Item $rootEnvPath apps/backend/.env -Force
    $rootEnvLines = Get-Content $rootEnvPath
} else {
    Write-Host "No se encontró .env.local. Crea uno basado en .env.production" -ForegroundColor Red
    exit 1
}

function Get-EnvValue {
    param([string[]]$lines, [string]$key, [string]$default = "")
    if (-not $lines) { return $default }
    $match = $lines | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
    if (-not $match) { return $default }
    return ($match.Split("=", 2)[1]).Trim().Trim('"').Trim("'")
}

function Get-PortFromUrl {
    param([string]$url, [int]$fallback)
    try {
        $uri = [System.Uri]$url
        if ($uri.Port -gt 0) { return $uri.Port }
    } catch {}
    return $fallback
}

Write-Host "[2/6] Verificando DB local (PostgreSQL en localhost:5432)..." -ForegroundColor Yellow
# Asume PostgreSQL corriendo nativamente. Si no, instala y ejecuta.

Write-Host "[3/6] Iniciando Redis con Docker..." -ForegroundColor Yellow
docker run -d --name redis -p 6379:6379 redis --appendonly yes
if ($LASTEXITCODE -ne 0) {
    Write-Host "Redis ya está corriendo o error en Docker" -ForegroundColor Yellow
}

$repoRoot = Get-Location
$backendPath = Join-Path $repoRoot "apps/backend"
$adminPath = Join-Path $repoRoot "apps/admin"
$tenantPath = Join-Path $repoRoot "apps/tenant"
$venvActivate = Join-Path $repoRoot ".venv/Scripts/Activate.ps1"

$defaultApiUrl = "http://localhost:8000/api"
$frontendUrl = Get-EnvValue -lines $rootEnvLines -key "FRONTEND_URL" -default "http://localhost:8081"
$tenantOrigin = Get-EnvValue -lines $rootEnvLines -key "TENANT_URL" -default "http://localhost:8082"
$apiUrl = Get-EnvValue -lines $rootEnvLines -key "API_URL" -default $defaultApiUrl
if (-not $apiUrl) { $apiUrl = $defaultApiUrl }
Write-Host ("API_URL detectado: {0}" -f $apiUrl) -ForegroundColor Cyan
$adminPort = Get-PortFromUrl -url $frontendUrl -fallback 8081
$tenantPort = Get-PortFromUrl -url $tenantOrigin -fallback 8082

function To-WebsocketUrl {
    param([string]$httpUrl)
    if ($httpUrl -match "^https") { return $httpUrl -replace "^https", "wss" }
    return $httpUrl -replace "^http", "ws"
}

$adminEnvVars = @{
    "VITE_API_URL"       = $apiUrl
    "VITE_ADMIN_ORIGIN"  = $frontendUrl
    "VITE_TENANT_ORIGIN" = $tenantOrigin
    "VITE_BASE_PATH"     = "/"
}
$tenantEnvVars = @{
    "VITE_API_URL"       = $apiUrl
    "VITE_ADMIN_ORIGIN"  = $frontendUrl
    "VITE_TENANT_ORIGIN" = $tenantOrigin
    "VITE_BASE_PATH"     = "/"
    "VITE_WS_URL"        = To-WebsocketUrl -httpUrl $apiUrl
}

Write-Host "[4/6] Aplicando migraciones..." -ForegroundColor Yellow
Set-Location $backendPath
# Asegurar DATABASE_URL en entorno para Alembic
$envFile = Join-Path $backendPath ".env"
if (Test-Path $envFile) {
    $dbUrl = Get-Content $envFile | Where-Object { $_ -match "^DATABASE_URL=" } | ForEach-Object { $_.Split("=", 2)[1].Trim().Trim('"').Trim("'") }
    if ($dbUrl) { [Environment]::SetEnvironmentVariable("DATABASE_URL", $dbUrl, "Process") }
}
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error aplicando migraciones" -ForegroundColor Red
    exit $LASTEXITCODE
}
Set-Location $repoRoot

Write-Host "[5/6] Iniciando backend..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    & $using:venvActivate
    Set-Location $using:backendPath
    uvicorn app.main:app --host 0.0.0.0 --port 8000
} -Name backend

Write-Host "[6/6] Iniciando frontends..." -ForegroundColor Green
$adminJob = Start-Job -ScriptBlock {
    param($path, $envVars, $port)
    foreach ($entry in $envVars.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
    Set-Location $path
    npx --yes vite --host 0.0.0.0 --port $port --strictPort
} -Name admin -ArgumentList $adminPath, $adminEnvVars, $adminPort
$tenantJob = Start-Job -ScriptBlock {
    param($path, $envVars, $port)
    foreach ($entry in $envVars.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
    Set-Location $path
    npx --yes vite --host 0.0.0.0 --port $port --strictPort
} -Name tenant -ArgumentList $tenantPath, $tenantEnvVars, $tenantPort

Write-Host "`n[OK] Sistema listo (como en PRO)" -ForegroundColor Green
Write-Host "API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "Admin: $frontendUrl" -ForegroundColor White
Write-Host "Tenant: $tenantOrigin" -ForegroundColor White
Write-Host ""
Write-Host "Tips: Usa 'Get-Job' y 'Receive-Job admin' para ver logs de los frontends." -ForegroundColor DarkGray

Write-Host "`nPresiona Enter para detener todo..."
Read-Host

# Detener jobs
Write-Host "Deteniendo servicios..." -ForegroundColor Yellow
Stop-Job -Name backend,admin,tenant
Remove-Job -Name backend,admin,tenant
docker stop redis
docker rm redis

Write-Host "Todo detenido." -ForegroundColor Green
