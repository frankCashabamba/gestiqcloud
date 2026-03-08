#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Ejecuta localmente los mismos checks que el CI de GitHub Actions.

.DESCRIPTION
    Reproduce los jobs principales de ci.yml, backend.yml, webapps.yml y db-pipeline.yml:
      1. Pre-commit hooks
      2. Backend: ruff lint, static guards, mypy, pytest
      3. Frontend (admin & tenant): typecheck, lint, build
      4. DB pipeline: ops/ci checks
      5. (Opcional) E2E con Playwright

.PARAMETER Skip
    Lista de stages a saltar. Valores: precommit, backend, frontend, db, e2e
    Ejemplo: -Skip precommit,e2e

.PARAMETER E2E
    Incluir tests E2E (Playwright). Desactivado por defecto.

.EXAMPLE
    .\scripts\local_ci.ps1
    .\scripts\local_ci.ps1 -Skip precommit,db
    .\scripts\local_ci.ps1 -E2E
#>
[CmdletBinding()]
param(
    [string]$Skip = "",
    [switch]$E2E
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$SkipSet = if ($Skip) { $Skip -split "," | ForEach-Object { $_.Trim().ToLower() } } else { @() }

$passed  = [System.Collections.Generic.List[string]]::new()
$failed  = [System.Collections.Generic.List[string]]::new()
$skipped = [System.Collections.Generic.List[string]]::new()

function Write-Stage($name) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $name" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Run-Step {
    param(
        [string]$Stage,
        [string]$StepName,
        [scriptblock]$Command,
        [string]$WorkDir = $Root,
        [switch]$NonBlocking
    )
    Write-Host ""
    Write-Host ">> $StepName" -ForegroundColor Yellow

    Push-Location $WorkDir
    try {
        & $Command
        if ($LASTEXITCODE -ne 0 -and !$NonBlocking) {
            Write-Host "   FAIL: $StepName" -ForegroundColor Red
            $failed.Add("$Stage / $StepName")
        } elseif ($LASTEXITCODE -ne 0 -and $NonBlocking) {
            Write-Host "   WARN (non-blocking): $StepName" -ForegroundColor DarkYellow
            $passed.Add("$Stage / $StepName (warn)")
        } else {
            Write-Host "   OK: $StepName" -ForegroundColor Green
            $passed.Add("$Stage / $StepName")
        }
    } catch {
        if ($NonBlocking) {
            Write-Host "   WARN (non-blocking): $StepName - $_" -ForegroundColor DarkYellow
            $passed.Add("$Stage / $StepName (warn)")
        } else {
            Write-Host "   FAIL: $StepName - $_" -ForegroundColor Red
            $failed.Add("$Stage / $StepName")
        }
    } finally {
        Pop-Location
    }
}

$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# ============================================================================
# 1. PRE-COMMIT
# ============================================================================
if ("precommit" -notin $SkipSet) {
    Write-Stage "1/5  PRE-COMMIT HOOKS"
    Run-Step -Stage "pre-commit" -StepName "pre-commit run --all-files" -Command {
        python -m pre_commit run --all-files
    }
} else {
    $skipped.Add("pre-commit")
}

# ============================================================================
# 2. BACKEND
# ============================================================================
if ("backend" -notin $SkipSet) {
    Write-Stage "2/5  BACKEND CHECKS"
    $backendDir = Join-Path $Root "apps\backend"

    # Ruff lint
    Run-Step -Stage "backend" -StepName "Ruff lint" -WorkDir $backendDir -Command {
        ruff check --line-length=100 app/
    }

    # Static guard: forbid legacy ::uuid param casts
    Run-Step -Stage "backend" -StepName "Static guard: no legacy ::uuid casts" -WorkDir $backendDir -Command {
        $hits = Select-String -Path (Get-ChildItem -Path app -Recurse -Include *.py) `
            -Pattern ':[A-Za-z_][A-Za-z0-9_]*::uuid' -CaseSensitive |
            Where-Object { $_.Path -notmatch 'rls\.py' -and $_.Path -notmatch 'alembic' -and $_.Path -notmatch 'tests' }
        if ($hits) {
            $hits | ForEach-Object { Write-Host $_ }
            Write-Error "Found legacy ::uuid casts. Replace with CAST(:param AS uuid)."
            exit 1
        } else {
            Write-Host "OK: no legacy ::uuid casts found"
        }
    }

    # Static guard: forbid direct current_setting
    Run-Step -Stage "backend" -StepName "Static guard: no direct current_setting" -WorkDir $backendDir -Command {
        $hits = Select-String -Path (Get-ChildItem -Path app -Recurse -Include *.py) `
            -Pattern "current_setting\('app\.tenant_id'" -CaseSensitive |
            Where-Object { $_.Path -notmatch 'rls\.py' -and $_.Path -notmatch 'alembic' -and $_.Path -notmatch 'tests' }
        if ($hits) {
            $hits | ForEach-Object { Write-Host $_ }
            Write-Error "Found direct current_setting usage. Use tenant_id_sql_expr()."
            exit 1
        } else {
            Write-Host "OK: no direct current_setting usages found"
        }
    }

    # Mypy (non-blocking)
    Run-Step -Stage "backend" -StepName "mypy (non-blocking)" -WorkDir $backendDir -NonBlocking -Command {
        mypy app/ --ignore-missing-imports
    }

    # Pytest
    Run-Step -Stage "backend" -StepName "pytest" -WorkDir $backendDir -Command {
        $env:ENV = "test"
        $env:SECRET_KEY = "test-secret-key"
        $env:JWT_SECRET_KEY = "test-jwt-key"
        $env:FRONTEND_URL = "http://localhost:5173"
        $env:TENANT_NAMESPACE_UUID = "00000000-0000-0000-0000-000000000000"
        pytest app/tests -v --tb=short --cov=app --cov-report=term --ignore=app/tests/modules/imports/
    }
} else {
    $skipped.Add("backend")
}

# ============================================================================
# 3. FRONTEND (admin + tenant)
# ============================================================================
if ("frontend" -notin $SkipSet) {
    Write-Stage "3/5  FRONTEND CHECKS"

    foreach ($app in @("admin", "tenant")) {
        $appDir = Join-Path $Root "apps\$app"
        if (-not (Test-Path (Join-Path $appDir "package.json"))) {
            Write-Host "  Skipping $app (no package.json)" -ForegroundColor DarkYellow
            $skipped.Add("frontend/$app")
            continue
        }

        Run-Step -Stage "frontend/$app" -StepName "$app - npm ci" -WorkDir $appDir -Command {
            npm ci --no-audit --no-fund
        }

        Run-Step -Stage "frontend/$app" -StepName "$app - typecheck" -WorkDir $appDir -Command {
            npm run typecheck
        }

        Run-Step -Stage "frontend/$app" -StepName "$app - lint" -WorkDir $appDir -Command {
            npm run lint -- --max-warnings 1000
        }

        $env:VITE_API_URL = "http://localhost:8000"
        Run-Step -Stage "frontend/$app" -StepName "$app - build" -WorkDir $appDir -Command {
            npm run build
        }

        Run-Step -Stage "frontend/$app" -StepName "$app - unit tests" -WorkDir $appDir -NonBlocking -Command {
            npm run test:run
        }
    }
} else {
    $skipped.Add("frontend")
}

# ============================================================================
# 4. DB PIPELINE
# ============================================================================
if ("db" -notin $SkipSet) {
    Write-Stage "4/5  DB PIPELINE CHECKS"

    Run-Step -Stage "db-pipeline" -StepName "ops/ci/checks.py" -WorkDir $Root -Command {
        python ops/ci/checks.py
    }
} else {
    $skipped.Add("db-pipeline")
}

# ============================================================================
# 5. E2E (solo si se pide)
# ============================================================================
if ($E2E -and "e2e" -notin $SkipSet) {
    Write-Stage "5/5  E2E TESTS (Playwright)"

    Run-Step -Stage "e2e" -StepName "Install Playwright browsers" -WorkDir $Root -Command {
        npx playwright install --with-deps chromium
    }

    Run-Step -Stage "e2e" -StepName "Playwright tests" -WorkDir $Root -NonBlocking -Command {
        $env:CI = "true"
        $env:VITE_API_URL = "http://localhost:8000/api"
        npx playwright test --project=chromium
    }
} else {
    $skipped.Add("e2e")
}

# ============================================================================
# SUMMARY
# ============================================================================
$Stopwatch.Stop()
$elapsed = $Stopwatch.Elapsed

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  CI LOCAL - RESUMEN" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

if ($passed.Count -gt 0) {
    Write-Host "PASSED ($($passed.Count)):" -ForegroundColor Green
    $passed | ForEach-Object { Write-Host "  ✅ $_" -ForegroundColor Green }
}
if ($skipped.Count -gt 0) {
    Write-Host ""
    Write-Host "SKIPPED ($($skipped.Count)):" -ForegroundColor DarkYellow
    $skipped | ForEach-Object { Write-Host "  ⏭️  $_" -ForegroundColor DarkYellow }
}
if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "FAILED ($($failed.Count)):" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  ❌ $_" -ForegroundColor Red }
}

Write-Host ""
Write-Host "Tiempo total: $($elapsed.Minutes)m $($elapsed.Seconds)s" -ForegroundColor Cyan
Write-Host ""

if ($failed.Count -gt 0) {
    Write-Host "❌ CI LOCAL FALLÓ" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ CI LOCAL PASÓ" -ForegroundColor Green
    exit 0
}
