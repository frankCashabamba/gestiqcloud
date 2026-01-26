#!/bin/bash
# Apply migration for POSLine polymorphic model support
# Archivo: ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql

set -e

# Configuration
DB_USER="${DB_USER:-gestiqcloud_user}"
DB_NAME="${DB_NAME:-gestiqcloud}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "Applying migration: 2026-01-22_001_add_pos_invoice_lines"
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo ""

# Execute migration
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql

echo ""
echo "✅ Migration applied successfully"
echo ""
echo "Verifying table creation..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -c "\dt pos_invoice_lines"

echo ""
echo "Verifying index creation..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -c "\di idx_pos_invoice_lines*"

echo ""
echo "✅ All verified successfully!"
