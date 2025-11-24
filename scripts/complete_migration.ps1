# PowerShell Script: Complete Spanish to English migration
# RUN FROM: proyecto root directory
# USAGE: .\scripts\complete_migration.ps1 -Execute

param(
    [switch]$Execute = $false
)

$mode = if ($Execute) { "EXECUTE" } else { "DRY RUN" }
Write-Host "======================================"
Write-Host "Complete Spanish→English Migration"
Write-Host "Mode: $mode"
Write-Host "======================================"
Write-Host ""

# ============================================
# STEP 1: Delete empresa/ folder
# ============================================
Write-Host "STEP 1: Delete empresa/ folder (duplicate of company/)"
Write-Host "---"

$empresaPath = "apps\backend\app\models\empresa"
if (Test-Path $empresaPath) {
    Write-Host "  Found: $empresaPath" -ForegroundColor Yellow
    if ($Execute) {
        Remove-Item -Path $empresaPath -Recurse -Force
        Write-Host "  ✓ Deleted successfully" -ForegroundColor Green
    } else {
        Write-Host "  [DRY RUN] Would delete this folder" -ForegroundColor Gray
    }
} else {
    Write-Host "  Already deleted or not found" -ForegroundColor Green
}
Write-Host ""

# ============================================
# STEP 2: Rename files in accounting/
# ============================================
Write-Host "STEP 2: Rename accounting/plan_cuentas.py → chart_of_accounts.py"
Write-Host "---"

$files = @(
    @{ oldPath = "apps\backend\app\models\accounting\plan_cuentas.py"; newName = "chart_of_accounts.py"; desc = "Plan de Cuentas" },
    @{ oldPath = "apps\backend\app\models\finance\caja.py"; newName = "cash_management.py"; desc = "Caja" },
    @{ oldPath = "apps\backend\app\models\hr\nomina.py"; newName = "payroll.py"; desc = "Nómina" },
    @{ oldPath = "apps\backend\app\models\hr\empleado.py"; newName = "employee.py"; desc = "Empleado" },
    @{ oldPath = "apps\backend\app\models\core\auditoria_importacion.py"; newName = "import_audit.py"; desc = "Auditoría Importación" }
)

foreach ($file in $files) {
    if (Test-Path $file.oldPath) {
        Write-Host "  [$($file.desc)] Renaming..."
        if ($Execute) {
            $dir = Split-Path -Path $file.oldPath
            Rename-Item -Path $file.oldPath -NewName $file.newName
            Write-Host "    ✓ $($file.oldPath) → $($file.newName)" -ForegroundColor Green
        } else {
            Write-Host "    [DRY RUN] Would rename: $($file.oldPath)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ✗ NOT FOUND: $($file.oldPath)" -ForegroundColor Red
    }
}
Write-Host ""

# ============================================
# STEP 3: Update class names in files
# ============================================
Write-Host "STEP 3: Update class names in renamed files"
Write-Host "---"

$classReplacements = @(
    @{
        file = "apps\backend\app\models\accounting\chart_of_accounts.py"
        replacements = @(
            @{ old = "class PlanCuentas"; new = "class ChartOfAccounts" },
            @{ old = "class Cuenta"; new = "class Account" }
        )
    },
    @{
        file = "apps\backend\app\models\finance\cash_management.py"
        replacements = @(
            @{ old = "class Caja"; new = "class CashManagement" },
            @{ old = "class CajaMovimiento"; new = "class CashMovement" },
            @{ old = "class CierreCaja"; new = "class CashClosing" }
        )
    },
    @{
        file = "apps\backend\app\models\hr\payroll.py"
        replacements = @(
            @{ old = "class Nomina"; new = "class Payroll" },
            @{ old = "class NominaConcepto"; new = "class PayrollItem" },
            @{ old = "class NominaPlantilla"; new = "class PayrollTemplate" }
        )
    }
)

foreach ($item in $classReplacements) {
    if (Test-Path $item.file) {
        Write-Host "  Updating: $($item.file)"
        if ($Execute) {
            $content = Get-Content -Path $item.file -Raw -Encoding UTF8
            foreach ($replacement in $item.replacements) {
                $content = $content -replace [regex]::Escape($replacement.old), $replacement.new
            }
            Set-Content -Path $item.file -Value $content -Encoding UTF8
            Write-Host "    ✓ Updated class names" -ForegroundColor Green
        } else {
            Write-Host "    [DRY RUN] Would update class names" -ForegroundColor Gray
        }
    }
}
Write-Host ""

# ============================================
# STEP 4: Update __init__.py imports
# ============================================
Write-Host "STEP 4: Update __init__.py files"
Write-Host "---"

$initFiles = @(
    @{
        path = "apps\backend\app\models\accounting\__init__.py"
        replacements = @(
            @{ old = "from .plan_cuentas import"; new = "from .chart_of_accounts import" }
        )
    },
    @{
        path = "apps\backend\app\models\finance\__init__.py"
        replacements = @(
            @{ old = "from .caja import"; new = "from .cash_management import" }
        )
    },
    @{
        path = "apps\backend\app\models\hr\__init__.py"
        replacements = @(
            @{ old = "from .nomina import"; new = "from .payroll import" },
            @{ old = "from .empleado import"; new = "from .employee import" }
        )
    },
    @{
        path = "apps\backend\app\models\core\__init__.py"
        replacements = @(
            @{ old = "from .auditoria_importacion import"; new = "from .import_audit import" }
        )
    }
)

foreach ($item in $initFiles) {
    if (Test-Path $item.path) {
        Write-Host "  Updating: $($item.path)"
        if ($Execute) {
            $content = Get-Content -Path $item.path -Raw -Encoding UTF8
            foreach ($replacement in $item.replacements) {
                $content = $content -replace [regex]::Escape($replacement.old), $replacement.new
            }
            Set-Content -Path $item.path -Value $content -Encoding UTF8
            Write-Host "    ✓ Updated imports" -ForegroundColor Green
        } else {
            Write-Host "    [DRY RUN] Would update imports" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⓘ NOT FOUND: $($item.path) (might not have these imports)" -ForegroundColor Cyan
    }
}
Write-Host ""

# ============================================
# Summary
# ============================================
Write-Host "======================================"
Write-Host "Migration Summary"
Write-Host "======================================"
if ($Execute) {
    Write-Host "✓ Migration COMPLETED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "1. Run Python script to update remaining imports:"
    Write-Host "   python scripts/update_imports.py --apply"
    Write-Host ""
    Write-Host "2. Search and replace in remaining files:"
    Write-Host "   - Update any direct references to Spanish class names"
    Write-Host "   - Update docstrings to English (if needed)"
    Write-Host ""
    Write-Host "3. Run tests:"
    Write-Host "   pytest tests/ -v"
} else {
    Write-Host "DRY RUN - No changes made" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To EXECUTE the migration, run:"
    Write-Host "  .\scripts\complete_migration.ps1 -Execute"
}
Write-Host ""
