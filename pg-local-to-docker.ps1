<#  scripts/pg-local-to-docker.ps1

Copia la BD del Postgres del HOST (local) al Postgres del contenedor Docker (servicio "db").

Requisitos:
- Tener "docker compose" funcionando y el servicio "db" levantado.
- Tener pg_dump/pg_restore en PATH (o indicar su ruta con -PgBin).
- PowerShell 5+.

Uso rápido (valores por defecto coinciden con tu proyecto):
  pwsh -File scripts/pg-local-to-docker.ps1 -LocalPassword "<PASS_LOCAL>"

Parámetros útiles:
  -LocalHost, -LocalPort, -LocalUser, -LocalDb
  -LocalPassword (puedes omitir y te preguntará)
  -ContainerService (por defecto 'db'), -ContainerDb, -ContainerUser, -ContainerPassword
  -Schema (por defecto 'public')
  -DumpFile (por defecto '.\dump_local.pgcustom')
  -PgBin (ruta a binarios de Postgres si no están en PATH; ej. 'C:\Program Files\PostgreSQL\15\bin')
#>

[CmdletBinding()]
param(
  # --- Origen (HOST local) ---
  [string]$LocalHost = "localhost",
  [int]$LocalPort = 5432,
  [string]$LocalUser = "postgres",
  [string]$LocalDb   = "gestiqclouddb_dev",
  [string]$LocalPassword,

  # --- Destino (contenedor Docker) ---
  [string]$ContainerService = "db",
  [string]$ContainerUser    = "postgres",
  [string]$ContainerDb      = "gestiqclouddb_dev",
  [string]$ContainerPassword = "root",

  # --- Opciones ---
  [string]$Schema   = "public",
  [string]$DumpFile = ".\dump_local.pgcustom",
  [string]$PgBin    = ""  # ej: 'C:\Program Files\PostgreSQL\15\bin'
)

$ErrorActionPreference = "Stop"

function Resolve-Bin([string]$name) {
  if ($PgBin -and (Test-Path (Join-Path $PgBin "$name.exe"))) {
    return (Join-Path $PgBin "$name.exe")
  }
  $p = (Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1).Source
  if ($p) { return $p }
  throw "No se encontró '$name'. Añádelo al PATH o indica -PgBin con la ruta a los binarios de Postgres."
}

$pg_dump    = Resolve-Bin "pg_dump"
$pg_restore = Resolve-Bin "pg_restore"

Write-Host "==> Verificando 'docker compose' y servicio '$ContainerService'..." -ForegroundColor Cyan
docker compose ps | Out-Null

# Comprobar que el servicio existe
$services = docker compose ps --services
if (-not ($services -contains $ContainerService)) {
  throw "No existe servicio '$ContainerService' en docker-compose. Servicios: $services"
}

# Pedir password local si no se pasó
if (-not $LocalPassword) {
  $LocalPassword = Read-Host -AsSecureString "Password del Postgres local ($LocalUser@$LocalHost)"
  $LocalPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($LocalPassword)
  )
}

$dumpPath = (Resolve-Path (Split-Path -Parent $DumpFile) -ErrorAction SilentlyContinue)
if (-not $dumpPath) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $DumpFile) -Force | Out-Null
}

Write-Host "==> Generando dump des de $LocalHost:$LocalPort DB=$LocalDb (schema=$Schema)..." -ForegroundColor Cyan
$env:PGPASSWORD = $LocalPassword
& $pg_dump `
  -h $LocalHost -p $LocalPort -U $LocalUser -d $LocalDb `
  -n $Schema -Fc --no-owner --no-privileges `
  -f $DumpFile
if ($LASTEXITCODE -ne 0) { throw "pg_dump falló (código $LASTEXITCODE)" }
$env:PGPASSWORD = $null
Write-Host "   Dump creado: $DumpFile" -ForegroundColor Green

$remoteDump = "/tmp/$(Split-Path -Leaf $DumpFile)"
Write-Host "==> Copiando dump al contenedor $ContainerService:$remoteDump ..." -ForegroundColor Cyan
docker compose cp $DumpFile "$ContainerService:$remoteDump"

Write-Host "==> Restaurando en contenedor (DB=$ContainerDb, user=$ContainerUser)..." -ForegroundColor Cyan
$restoreCmd = @"
PGPASSWORD=$ContainerPassword $pg_restore -U $ContainerUser -d $ContainerDb --clean --if-exists --no-owner --no-privileges $remoteDump
"@
docker compose exec $ContainerService sh -lc $restoreCmd

Write-Host "==> Verificando filas en $Schema.core_empresa ..." -ForegroundColor Cyan
$checkCmd = "PGPASSWORD=$ContainerPassword psql -U $ContainerUser -d $ContainerDb -c `"`"SELECT COUNT(*) FROM $Schema.core_empresa;`"`""
docker compose exec $ContainerService sh -lc $checkCmd

Write-Host "==> Limpiando dump del contenedor ..." -ForegroundColor Cyan
docker compose exec $ContainerService sh -lc "rm -f $remoteDump" | Out-Null

Write-Host "==> ¡Listo! Si el conteo es > 0, tu /api/v1/admin/empresas ya debería listar datos." -ForegroundColor Green
