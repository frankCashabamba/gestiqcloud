# PowerShell Script: Rename Spanish model files to English
# IMPORTANTE: Ejecutar desde la carpeta: apps/backend/app/models

param(
    [switch]$DryRun = $true
)

$ErrorActionPreference = "Stop"

Write-Host "======================================"
Write-Host "Renaming Spanish Model Files to English"
Write-Host "DryRun Mode: $DryRun"
Write-Host "======================================"
Write-Host ""

# Definir renombrados
$renames = @(
    # accounting
    @{
        path = "accounting\plan_cuentas.py"
        newName = "chart_of_accounts.py"
        description = "Chart of Accounts (plan de cuentas)"
    },
    # finance
    @{
        path = "finance\caja.py"
        newName = "cash_management.py"
        description = "Cash Management (caja)"
    },
    # hr
    @{
        path = "hr\nomina.py"
        newName = "payroll.py"
        description = "Payroll (nómina)"
    },
    @{
        path = "hr\empleado.py"
        newName = "employee.py"
        description = "Employee (empleado)"
    },
    # core
    @{
        path = "core\auditoria_importacion.py"
        newName = "import_audit.py"
        description = "Import Audit (auditoría importación)"
    }
)

# Step 1: Mostrar lo que se va a hacer
Write-Host "Files to be renamed:"
Write-Host "-------------------"
$renames | ForEach-Object {
    Write-Host "  [$($_.path)] -> [$($_.newName)]"
    Write-Host "    Description: $($_.description)"
}
Write-Host ""

# Step 2: Verificar que los archivos existen
Write-Host "Checking if files exist..."
$allExist = $true
$renames | ForEach-Object {
    $fullPath = "$pwd\$($_.path)"
    if (Test-Path $fullPath) {
        Write-Host "  ✓ $($_.path)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($_.path) - NOT FOUND" -ForegroundColor Red
        $allExist = $false
    }
}
Write-Host ""

if (-not $allExist) {
    Write-Host "ERROR: Some files not found. Aborting." -ForegroundColor Red
    exit 1
}

# Step 3: Realizar renombrados
if ($DryRun) {
    Write-Host "DRY RUN MODE - No changes made" -ForegroundColor Yellow
} else {
    Write-Host "Performing renames..."
    $renames | ForEach-Object {
        $oldPath = "$pwd\$($_.path)"
        $newPath = "$pwd\$($_.path.Replace($_.path.Split('\')[-1], $_.newName))"

        try {
            Rename-Item -Path $oldPath -NewName $_.newName -ErrorAction Stop
            Write-Host "  ✓ Renamed: $($_.path) -> $($_.newName)" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ FAILED: $($_.path)" -ForegroundColor Red
            Write-Host "    Error: $($_.Exception.Message)"
        }
    }
}

Write-Host ""
Write-Host "======================================"
Write-Host "Step 1 Complete: File renames"
Write-Host "======================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Update class names in renamed files"
Write-Host "2. Update imports in __init__.py files"
Write-Host "3. Update imports throughout app/"
Write-Host "4. Update docstrings to English"
Write-Host "5. Delete empresa/ folder (after verifying content)"
Write-Host ""
