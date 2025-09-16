param(
  [Parameter(Position=0)][string]$cmd = "help",
  [Parameter(Position=1)][string]$svc = "backend"
)

switch ($cmd) {
  'up' { docker compose up -d --build }
  'down' { docker compose down -v }
  'rebuild' { docker compose build --no-cache }
  'logs' { docker compose logs -f $svc }
  'typecheck' {
    pushd apps/admin; npm ci; npm run typecheck; popd
    pushd apps/tenant; npm ci; npm run typecheck; popd
  }
  default { Write-Host "Usage: scripts/init.ps1 {up|down|rebuild|logs [svc]|typecheck}" }
}

