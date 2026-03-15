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

$flushRedis = Read-Host "¿Limpiar Redis DB 0 (broker) y DB 1 (resultados) al iniciar? (s/N)"
if ($flushRedis -and $flushRedis.Trim().ToLower() -in @("s", "si", "sí", "y", "yes")) {
    try {
        $null = docker exec redis redis-cli -n 0 FLUSHDB 2>$null
        $brokerFlushed = $LASTEXITCODE -eq 0
        $null = docker exec redis redis-cli -n 1 FLUSHDB 2>$null
        $resultsFlushed = $LASTEXITCODE -eq 0
        if ($brokerFlushed -and $resultsFlushed) {
            Write-Host "Redis DB 0 (broker/payload) y DB 1 (resultados) limpiadas." -ForegroundColor Green
        } else {
            Write-Host "No se pudo limpiar Redis DB 0/1 por completo (redis-cli no disponible o Redis no levantado)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "No se pudo limpiar Redis DB 0/1." -ForegroundColor Yellow
    }
}

$backendPath = Join-Path $repoRoot "apps/backend"
$adminPath = Join-Path $repoRoot "apps/admin"
$tenantPath = Join-Path $repoRoot "apps/tenant"
$venvActivate = Join-Path $repoRoot ".venv/Scripts/Activate.ps1"
$backendLog = Join-Path $repoRoot "backend.log"
$buildLogsDir = Join-Path $repoRoot ".logs/start_local"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm no esta disponible en PATH. Instala Node.js/npm antes de iniciar." -ForegroundColor Red
    exit 1
}

$defaultApiUrl = "http://localhost:8000/api"
$frontendUrl = Get-EnvValue -lines $rootEnvLines -key "FRONTEND_URL" -default "http://localhost:8081"
$tenantOrigin = Get-EnvValue -lines $rootEnvLines -key "TENANT_URL" -default "http://localhost:8082"
$apiUrl = Get-EnvValue -lines $rootEnvLines -key "API_URL" -default $defaultApiUrl
if (-not $apiUrl) { $apiUrl = $defaultApiUrl }

$redisUrl = Get-EnvValue -lines $rootEnvLines -key "REDIS_URL" -default ""
$devRedisUrl = Get-EnvValue -lines $rootEnvLines -key "DEV_REDIS_URL" -default ""
$celeryResultBackend = Get-EnvValue -lines $rootEnvLines -key "CELERY_RESULT_BACKEND" -default ""

if (-not $redisUrl) {
    if ($devRedisUrl) {
        $redisUrl = $devRedisUrl
    } else {
        $redisUrl = "redis://localhost:6379/0"
    }
}
if (-not $devRedisUrl) {
    $devRedisUrl = $redisUrl
}
if (-not $celeryResultBackend) {
    $celeryResultBackend = "redis://localhost:6379/1"
}

Write-Host ("API_URL detectado: {0}" -f $apiUrl) -ForegroundColor Cyan
$adminPort = Get-PortFromUrl -url $frontendUrl -fallback 8081
$tenantPort = Get-PortFromUrl -url $tenantOrigin -fallback 8082

function To-WebsocketUrl {
    param([string]$httpUrl)
    if ($httpUrl -match "^https") { return $httpUrl -replace "^https", "wss" }
    return $httpUrl -replace "^http", "ws"
}

function Test-PortOpen {
    param([string]$TargetHost = "127.0.0.1", [int]$Port, [int]$TimeoutMs = 800)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($TargetHost, $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($iar) | Out-Null
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-Port {
    param([string]$Name, [int]$Port, [int]$TimeoutSec = 45)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortOpen -Port $Port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    Write-Host ("Timeout esperando {0} en puerto {1}" -f $Name, $Port) -ForegroundColor Red
    return $false
}

function Stop-ListenersOnPort {
    param([int]$Port)
    try {
        $lines = netstat -ano | Select-String -Pattern "^\s*TCP\s+.*:$Port\s+.*LISTENING\s+(\d+)\s*$"
        if (-not $lines) { return }

        $pids = @()
        foreach ($line in $lines) {
            $parts = ($line.ToString() -split "\s+") | Where-Object { $_ -and $_.Trim() -ne "" }
            if ($parts.Count -ge 5) {
                $pid = $parts[-1]
                if ($pid -match "^\d+$" -and $pid -ne "0") {
                    $pids += [int]$pid
                }
            }
        }

        $pids = $pids | Sort-Object -Unique
        foreach ($pid in $pids) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction Stop
                Write-Host "Proceso PID=$pid detenido en puerto $Port" -ForegroundColor Yellow
            } catch {
                Write-Host "No se pudo detener PID=$pid en puerto $Port (quizá sin permisos)." -ForegroundColor DarkYellow
            }
        }
    } catch {
        Write-Host "No se pudo inspeccionar puerto $Port" -ForegroundColor DarkYellow
    }
}

function Test-RequiredNodeModules {
    param([string]$AppPath, [string[]]$RequiredEntries)

    $missingEntries = @()
    $nodeModulesPath = Join-Path $AppPath "node_modules"

    if (-not (Test-Path $nodeModulesPath)) {
        return @("__node_modules__")
    }

    foreach ($entry in $RequiredEntries) {
        $entryPath = Join-Path $nodeModulesPath $entry
        if (-not (Test-Path $entryPath)) {
            $missingEntries += $entry
        }
    }

    return $missingEntries
}

function Invoke-NpmInApp {
    param(
        [string]$AppPath,
        [string[]]$NpmArgs,
        [hashtable]$EnvVars = @{},
        [string]$LogPath = ""
    )

    $previousEnv = @{}
    foreach ($entry in $EnvVars.GetEnumerator()) {
        $previousEnv[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, "Process")
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }

    Push-Location $AppPath
    try {
        if ($LogPath) {
            $logDir = Split-Path -Parent $LogPath
            if ($logDir) {
                New-Item -ItemType Directory -Force -Path $logDir | Out-Null
            }
            if (Test-Path $LogPath) {
                Remove-Item $LogPath -Force -ErrorAction SilentlyContinue
            }

            $joinedArgs = ($NpmArgs | ForEach-Object {
                if ($_ -match '\s|["]') {
                    '"' + ($_ -replace '"', '\"') + '"'
                } else {
                    $_
                }
            }) -join ' '

            $cmdLine = "npm $joinedArgs > `"$LogPath`" 2>&1"
            cmd.exe /d /c $cmdLine | Out-Null
        } else {
            & npm @NpmArgs
        }

        return $LASTEXITCODE
    } finally {
        Pop-Location
        foreach ($entry in $EnvVars.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($entry.Key, $previousEnv[$entry.Key], "Process")
        }
    }
}

function Ensure-FrontendDependencies {
    param(
        [string]$AppName,
        [string]$AppPath,
        [string[]]$RequiredEntries
    )

    $packageLockPath = Join-Path $AppPath "package-lock.json"
    $installedLockSnapshot = Join-Path $AppPath "node_modules/.package-lock.json"
    $missingEntries = Test-RequiredNodeModules -AppPath $AppPath -RequiredEntries $RequiredEntries
    $needsInstall = $missingEntries.Count -gt 0
    $reasons = @()

    if ($missingEntries -contains "__node_modules__") {
        $reasons += "node_modules no existe"
    } elseif ($missingEntries.Count -gt 0) {
        $reasons += ("faltan dependencias: {0}" -f (($missingEntries | Where-Object { $_ -ne "__node_modules__" }) -join ", "))
    }

    if ((Test-Path $packageLockPath) -and (Test-Path $installedLockSnapshot)) {
        $lockTime = (Get-Item $packageLockPath).LastWriteTimeUtc
        $snapshotTime = (Get-Item $installedLockSnapshot).LastWriteTimeUtc
        if ($lockTime -gt $snapshotTime) {
            $needsInstall = $true
            $reasons += "package-lock.json es mas reciente que la instalacion actual"
        }
    } elseif ((Test-Path $packageLockPath) -and (Test-Path (Join-Path $AppPath "node_modules")) -and -not (Test-Path $installedLockSnapshot)) {
        $needsInstall = $true
        $reasons += "node_modules no tiene snapshot de package-lock"
    }

    if (-not $needsInstall) {
        Write-Host ("Dependencias de {0}: OK" -f $AppName) -ForegroundColor Green
        return
    }

    Write-Host ("Preparando dependencias de {0}: {1}" -f $AppName, ($reasons -join "; ")) -ForegroundColor Yellow

    $logsDir = Join-Path $repoRoot ".logs/start_local"
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

    $ciLog = Join-Path $logsDir "$AppName-npm-ci.log"
    $installLog = Join-Path $logsDir "$AppName-npm-install.log"
    $installExit = 0
    $lastLogToShow = ""

    if (Test-Path $packageLockPath) {
        $installExit = Invoke-NpmInApp -AppPath $AppPath -NpmArgs @("ci", "--no-audit", "--no-fund") -LogPath $ciLog
        $lastLogToShow = $ciLog

        if ($installExit -ne 0) {
            Write-Host ("npm ci fallo en {0}; reintentando con npm install" -f $AppName) -ForegroundColor DarkYellow
            $installExit = Invoke-NpmInApp -AppPath $AppPath -NpmArgs @("install", "--no-audit", "--no-fund") -LogPath $installLog
            $lastLogToShow = $installLog
        }
    } else {
        $installExit = Invoke-NpmInApp -AppPath $AppPath -NpmArgs @("install", "--no-audit", "--no-fund") -LogPath $installLog
        $lastLogToShow = $installLog
    }

    if ($installExit -ne 0) {
        Write-Host ("No se pudieron instalar dependencias para {0}" -f $AppName) -ForegroundColor Red

        if (Test-Path $ciLog) {
            Write-Host ("Log npm ci: {0}" -f $ciLog) -ForegroundColor DarkYellow
        }
        if (Test-Path $installLog) {
            Write-Host ("Log npm install: {0}" -f $installLog) -ForegroundColor DarkYellow
        }

        if ($lastLogToShow -and (Test-Path $lastLogToShow)) {
            Write-Host ("Ultimas lineas de {0}:" -f $lastLogToShow) -ForegroundColor Yellow
            Get-Content $lastLogToShow -Tail 80 | Out-Host
        }

        exit 1
    }

    $remainingMissing = Test-RequiredNodeModules -AppPath $AppPath -RequiredEntries $RequiredEntries
    if ($remainingMissing.Count -gt 0) {
        Write-Host ("La instalacion de {0} termino, pero aun faltan: {1}" -f $AppName, ($remainingMissing -join ", ")) -ForegroundColor Red
        exit 1
    }
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
    "REDIS_URL"             = $redisUrl
    "DEV_REDIS_URL"         = $devRedisUrl
    "CELERY_RESULT_BACKEND" = $celeryResultBackend
    "CELERY_RESULT_EXPIRES" = "3600"
    "CELERY_IGNORE_RESULT"  = "false"
    "ENV_FILE"              = $rootEnvPath
    "CORS_ALLOW_HEADERS"    = '["Authorization","Content-Type","X-CSRF-Token","X-CSRFToken","X-CSRF","X-Client-Version","X-Client-Revision","X-Confirm-Delete-Tenant"]'
}

$cleanupPorts = Read-Host "¿Cerrar procesos previos en puertos 8000/$adminPort/$tenantPort antes de iniciar? (S/n)"
if (-not $cleanupPorts -or $cleanupPorts.Trim().ToLower() -in @("s", "si", "sí", "y", "yes")) {
    Stop-ListenersOnPort -Port 8000
    Stop-ListenersOnPort -Port $adminPort
    Stop-ListenersOnPort -Port $tenantPort
}

Write-Host "[4/7] Validando dependencias y build de frontends..." -ForegroundColor Yellow

$adminRequiredEntries = @(
    "vite\package.json",
    "@vitejs\plugin-react\package.json",
    "vite-plugin-pwa\package.json",
    "react-router-dom\package.json",
    "axios\package.json",
    "idb-keyval\package.json"
)

$tenantRequiredEntries = @(
    "vite\package.json",
    "@vitejs\plugin-react\package.json",
    "vite-plugin-pwa\package.json",
    "react-router-dom\package.json",
    "axios\package.json",
    "idb-keyval\package.json",
    "workbox-precaching\package.json"
)

Ensure-FrontendDependencies -AppName "admin" -AppPath $adminPath -RequiredEntries $adminRequiredEntries
Ensure-FrontendDependencies -AppName "tenant" -AppPath $tenantPath -RequiredEntries $tenantRequiredEntries

$adminBuildLog = Join-Path $buildLogsDir "admin-build.log"
$tenantBuildLog = Join-Path $buildLogsDir "tenant-build.log"

$adminBuildExit = Invoke-NpmInApp -AppPath $adminPath -EnvVars $adminEnvVars -NpmArgs @("run", "build") -LogPath $adminBuildLog
if ($adminBuildExit -ne 0) {
    Write-Host "Build de admin fallo. Corrige el frontend antes de iniciar el stack." -ForegroundColor Red
    if (Test-Path $adminBuildLog) {
        Write-Host ("Ultimas lineas de {0}:" -f $adminBuildLog) -ForegroundColor Yellow
        Get-Content $adminBuildLog -Tail 80 | Out-Host
    }
    exit 1
}

$tenantBuildExit = Invoke-NpmInApp -AppPath $tenantPath -EnvVars $tenantEnvVars -NpmArgs @("run", "build") -LogPath $tenantBuildLog
if ($tenantBuildExit -ne 0) {
    Write-Host "Build de tenant fallo. Corrige el frontend antes de iniciar el stack." -ForegroundColor Red
    if (Test-Path $tenantBuildLog) {
        Write-Host ("Ultimas lineas de {0}:" -f $tenantBuildLog) -ForegroundColor Yellow
        Get-Content $tenantBuildLog -Tail 80 | Out-Host
    }
    exit 1
}

Write-Host "[5/7] Iniciando backend..." -ForegroundColor Green

if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Host "No se encontro .venv. Crea el entorno virtual." -ForegroundColor Red
    exit 1
}

$venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"
$backendJob = Start-Job -ScriptBlock {
    param($envVars, $logPath, $pythonExe, $workDir)

    foreach ($entry in $envVars.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }

    Set-Location $workDir
    & $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 *>> $logPath
} -Name backend -ArgumentList $backendEnvVars, $backendLog, $venvPython, $backendPath

Write-Host "[6/7] Iniciando frontends..." -ForegroundColor Green

$adminJob = Start-Job -ScriptBlock {
    param($path, $envVars, $port)
    [Environment]::SetEnvironmentVariable("NODE_ENV", "development", "Process")
    foreach ($entry in $envVars.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
    Set-Location $path
    npm run dev -- --host 0.0.0.0 --port $port --strictPort
} -Name admin -ArgumentList $adminPath, $adminEnvVars, $adminPort

$tenantJob = Start-Job -ScriptBlock {
    param($path, $envVars, $port)
    [Environment]::SetEnvironmentVariable("NODE_ENV", "development", "Process")
    foreach ($entry in $envVars.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
    Set-Location $path
    npm run dev -- --host 0.0.0.0 --port $port --strictPort
} -Name tenant -ArgumentList $tenantPath, $tenantEnvVars, $tenantPort

Write-Host "[6.5/7] Verificando puertos..." -ForegroundColor Yellow
$okBackend = Wait-Port -Name "backend" -Port 8000
$okAdmin = Wait-Port -Name "admin" -Port $adminPort
$okTenant = Wait-Port -Name "tenant" -Port $tenantPort

Start-Sleep -Seconds 2
$allJobNames = @("backend", "admin", "tenant")

if (-not ($okBackend -and $okAdmin -and $okTenant)) {
    Write-Host "`nAlguno de los servicios no levanto correctamente." -ForegroundColor Red
    Write-Host "Estado de jobs:" -ForegroundColor Yellow
    Get-Job -Name $allJobNames | Select-Object Id, Name, State, HasMoreData | Format-Table -AutoSize | Out-Host

    Write-Host "`nSalida de jobs (ultimas lineas):" -ForegroundColor Yellow
    Receive-Job -Name $allJobNames -Keep | Select-Object -Last 80 | Out-Host

    if (Test-Path $backendLog) {
        Write-Host "`nbackend.log (ultimas 80 lineas):" -ForegroundColor Yellow
        Get-Content $backendLog -Tail 80 | Out-Host
    }

    Stop-Job -Name $allJobNames -ErrorAction SilentlyContinue
    Remove-Job -Name $allJobNames -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "`n[OK] Sistema listo (como en PRO)" -ForegroundColor Green
Write-Host "API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "Admin: $frontendUrl" -ForegroundColor White
Write-Host "Tenant: $tenantOrigin" -ForegroundColor White
Write-Host ""
Write-Host "Tips: Usa 'Get-Job' y 'Receive-Job -Name backend|admin|tenant -Keep' para ver logs." -ForegroundColor DarkGray
Write-Host ("Para detener: Stop-Job -Name {0}; Remove-Job -Name {0}" -f ($allJobNames -join ",")) -ForegroundColor DarkGray
Write-Host "Celery no se inicia desde este script; arrancalo aparte cuando lo necesites." -ForegroundColor DarkGray
Write-Host "Redis (opcional): docker stop redis; docker rm redis" -ForegroundColor DarkGray
Write-Host "`nLos servicios quedan ejecutandose en segundo plano en esta sesion." -ForegroundColor Green

$showBackendTail = Read-Host "¿Ver backend.log en vivo ahora? (S/n)"
if (-not $showBackendTail -or $showBackendTail.Trim().ToLower() -in @("s", "si", "sí", "y", "yes")) {
    if (Test-Path $backendLog) {
        Write-Host "`nMostrando backend.log en vivo. Presiona Ctrl+C para salir del seguimiento (los jobs siguen activos)." -ForegroundColor Cyan
        Get-Content $backendLog -Tail 80 -Wait
    } else {
        Write-Host "No se encontró backend.log en: $backendLog" -ForegroundColor Yellow
    }
}