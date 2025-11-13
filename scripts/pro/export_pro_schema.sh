#!/usr/bin/env bash
set -euo pipefail

DB_NAME=${1:-gestiqclouddb_dev}
CONTAINER=${2:-db}
OUTPUT=${3:-ops/pro_schema.sql}

echo "Exporting schema from container '${CONTAINER}' DB '${DB_NAME}' to '${OUTPUT}'..."

# Ensure migrations are applied beforehand:
#   DB_DSN=postgresql://postgres:root@localhost:5432/${DB_NAME} \
#   python scripts/py/bootstrap_imports.py --dir ops/migrations

docker exec "${CONTAINER}" bash -lc "pg_dump -U postgres -s -x -O -d ${DB_NAME}" > "${OUTPUT}"

echo "Schema exported to ${OUTPUT}"

