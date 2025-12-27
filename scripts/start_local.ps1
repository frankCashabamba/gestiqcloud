Write-Host "=== GestiQCloud - Inicio Local (sin Docker, como en PRO) ===" -ForegroundColor Cyan

Write-Host "[1/7] Preparando .env..." -ForegroundColor Yellow
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$rootEnvPath = Join-Path $repoRoot ".env.local"
if (Test-Path $rootEnvPath) {
    Copy-Item $rootEnvPath (Join-Path $repoRoot "apps/backend/.env") -Force
    $rootEnvLines = Get-Content $rootEnvPath
} else {
    Write-Host "No se encontro .env.local. Crea uno basado en .env.production" -ForegroundColor Red
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

Write-Host "[2/7] Verificando DB local (PostgreSQL en localhost:5432)..." -ForegroundColor Yellow
# Asume PostgreSQL corriendo nativamente. Si no, instala y ejecuta.

Write-Host "[3/7] Iniciando Redis con Docker..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $redisStarted = $false
    $startResult = docker start redis 2>$null
    if ($LASTEXITCODE -eq 0) {
        $redisStarted = $true
        Write-Host "Redis ya estaba creado, iniciado." -ForegroundColor Green
    }
    if (-not $redisStarted) {
        docker run -d --name redis -p 6379:6379 redis --appendonly yes
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Redis ya esta corriendo o error en Docker" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Docker no esta disponible. Inicia Redis manualmente si es necesario." -ForegroundColor Yellow
}
$flushRedis = Read-Host "¿Limpiar Redis resultados (DB 1) al iniciar? (s/N)"
if ($flushRedis -and $flushRedis.Trim().ToLower() -in @("s", "si", "sí", "y", "yes")) {
    try {
        $null = docker exec redis redis-cli -n 1 FLUSHDB 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Redis DB 1 limpiada." -ForegroundColor Green
        } else {
            Write-Host "No se pudo limpiar Redis DB 1 (redis-cli no disponible o Redis no levantado)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "No se pudo limpiar Redis DB 1." -ForegroundColor Yellow
    }
}
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
$backendEnvVars = @{
    "REDIS_RESULT_URL"     = "redis://localhost:6379/1"
    "CELERY_RESULT_EXPIRES" = "3600"
    "CELERY_IGNORE_RESULT"  = "false"
}

Write-Host "[4/7] Aplicando migraciones..." -ForegroundColor Yellow
Set-Location $backendPath
# Activar venv
if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Host "No se encontro .venv. Crea el entorno virtual antes de migrar." -ForegroundColor Red
    exit 1
}
# Asegurar DATABASE_URL en entorno
$envFile = Join-Path $backendPath ".env"
if (Test-Path $envFile) {
    $dbUrl = Get-Content $envFile | Where-Object { $_ -match "^DATABASE_URL=" } | ForEach-Object { $_.Split("=", 2)[1].Trim().Trim('"').Trim("'") }
    if ($dbUrl) { [Environment]::SetEnvironmentVariable("DATABASE_URL", $dbUrl, "Process") }
}
Set-Location $repoRoot
python .\ops\scripts\migrate_all_migrations_idempotent.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error aplicando migraciones" -ForegroundColor Red
    exit $LASTEXITCODE
}
Set-Location $repoRoot

Write-Host "[5/7] Iniciando backend..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($envVars)
    foreach ($entry in $envVars.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
    & $using:venvActivate
    Set-Location $using:backendPath
    uvicorn app.main:app --host 0.0.0.0 --port 8000
} -Name backend -ArgumentList $backendEnvVars

Write-Host "[6/7] Iniciando frontends..." -ForegroundColor Green
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
Write-Host "Tips: Usa 'Get-Job' y 'Receive-Job backend|admin|tenant' para ver logs." -ForegroundColor DarkGray

Write-Host "`nPresiona Enter para detener todo..."
Read-Host

# Detener jobs
Write-Host "Deteniendo servicios..." -ForegroundColor Yellow
Stop-Job -Name backend,admin,tenant
Remove-Job -Name backend,admin,tenant
docker stop redis
docker rm redis

Write-Host "Todo detenido." -ForegroundColor Green
