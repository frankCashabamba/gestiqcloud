# Script to rename schema files
$base = "c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\schemas"

cd $base

# Define mappings
$mappings = @{
    "empresa.py" = "company.py"
    "rol_empresa.py" = "company_role.py"
    "hr_nomina.py" = "payroll.py"
    "configuracionempresasinicial.py" = "company_initial_config.py"
}

Write-Host "Current schema files:"
Get-ChildItem -Filter "*.py" | Select-Object -First 30 | %{ Write-Host "  - $_" }

Write-Host "`nMoving schema files..."
foreach ($old in $mappings.Keys) {
    $new = $mappings[$old]

    if (Test-Path $old) {
        Write-Host "Moving $old to $new"
        Move-Item $old $new -Force
        Write-Host "Successfully moved $old to $new"
    } else {
        Write-Host "$old does not exist (already moved?)"
    }
}

Write-Host "`nSchema files after move:"
Get-ChildItem -Filter "*.py" | Select-Object -First 30 | %{ Write-Host "  - $_" }
