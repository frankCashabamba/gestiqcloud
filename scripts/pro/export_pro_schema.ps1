param(
  [string]$Database = "gestiqclouddb_dev",
  [string]$Container = "db",
  [string]$Output = "ops/pro_schema.sql"
)

Write-Host "Exporting schema from container '$Container' DB '$Database' to '$Output'..."

# Ensure migrations are applied beforehand (outside of this script):
#   python scripts/py/bootstrap_imports.py --dir ops/migrations

$cmd = "pg_dump -U postgres -s -x -O -d $Database"

try {
  docker exec $Container bash -lc $cmd | Out-File -FilePath $Output -Encoding utf8
  Write-Host "Schema exported to $Output"
}
catch {
  Write-Error "Failed to export schema: $_"
  exit 1
}
