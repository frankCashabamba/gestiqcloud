# Script to delete legacy compat files
$base = "c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models\company"

cd $base

Write-Host "Current files in company/:"
Get-ChildItem -Filter "*.py" | Where-Object { $_.Name -notmatch "^__" } | %{ Write-Host "  - $_" }

# Define legacy files to delete
$legacyFiles = @("empresa.py", "usuarioempresa.py")

Write-Host "`nChecking for legacy files..."
foreach ($file in $legacyFiles) {
    if (Test-Path $file) {
        Write-Host "Deleting legacy file: $file"
        Remove-Item $file -Force
        Write-Host "Successfully deleted $file"
    } else {
        Write-Host "$file does not exist (already deleted?)"
    }
}

Write-Host "`nFiles in company/ after cleanup:"
Get-ChildItem -Filter "*.py" | Where-Object { $_.Name -notmatch "^__" } | %{ Write-Host "  - $_" }
