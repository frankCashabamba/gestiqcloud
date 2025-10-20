param(
  [string]$TestsPath = "app/tests",
  [switch]$Reinstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "[init-tests] $msg" -ForegroundColor Cyan }

# Resolve repo root as the parent of this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

# Python venv
$VenvDir = Join-Path $RepoRoot ".venv"
if (-not (Test-Path $VenvDir) -or $Reinstall) {
  Write-Step "Creating virtualenv at $VenvDir"
  py -m venv $VenvDir
}

Write-Step "Activating virtualenv"
& (Join-Path $VenvDir "Scripts\Activate.ps1")

Write-Step "Upgrading pip + installing backend requirements"
python -m pip install -U pip
pip install -r (Join-Path $RepoRoot "apps\backend\requirements.txt")

# Minimal test env vars
Write-Step "Setting test environment variables"
$env:PYTHONPATH = "$RepoRoot;$RepoRoot\apps;$RepoRoot\apps\backend"
$env:DATABASE_URL = "sqlite:///./test.db"
$env:FRONTEND_URL = "http://localhost:8081"
$env:TENANT_NAMESPACE_UUID = "00000000-0000-0000-0000-000000000000"
$env:TEST_MINIMAL = "1"

# Normalize test path relative to backend cwd
$NormalizedTestsPath = $TestsPath -replace "^[\\/]*apps[\\/]+backend[\\/]+", ""
if ([string]::IsNullOrWhiteSpace($NormalizedTestsPath)) { $NormalizedTestsPath = "app/tests" }

Write-Step "Running pytest ($NormalizedTestsPath)"
Set-Location (Join-Path $RepoRoot "apps\backend")
pytest -ra $NormalizedTestsPath
