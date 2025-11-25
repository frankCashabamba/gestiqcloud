# Script to move modules
$base = "c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\modules"

cd $base

# Define mappings
$mappings = @{
    "empresa" = "company"
    "usuarios" = "users"
    "rrhh" = "hr"
}

foreach ($old in $mappings.Keys) {
    $new = $mappings[$old]

    if (Test-Path $old) {
        Write-Host "Found: $old"
        if (-not (Test-Path $new)) {
            Write-Host "Moving $old to $new"
            Move-Item $old $new
            Write-Host "Successfully moved $old to $new"
        } else {
            Write-Host "$new already exists, skipping"
        }
    } else {
        Write-Host "$old does not exist"
    }
}

# List all directories
Write-Host "`nCurrent directories:"
Get-ChildItem -Directory | %{ Write-Host "  - $_" }
