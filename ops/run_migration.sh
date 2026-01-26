#!/bin/bash
# Migration runner script - Execute SQL migrations without alembic

set -e

# Configuration
DB_USER="${DB_USER:-gestiqcloud_user}"
DB_NAME="${DB_NAME:-gestiqcloud}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
MIGRATIONS_DIR="$(dirname "$0")/migrations"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Usage
usage() {
    echo "Usage: $0 [up|down|status] [migration_name]"
    echo ""
    echo "Examples:"
    echo "  $0 up 2026-01-22_001_add_pos_invoice_lines"
    echo "  $0 down 2026-01-22_001_add_pos_invoice_lines"
    echo "  $0 status"
    exit 1
}

# Check if migration directory exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}Error: Migrations directory not found at $MIGRATIONS_DIR${NC}"
    exit 1
fi

# Get command
COMMAND="${1:-status}"
MIGRATION="${2:-}"

case "$COMMAND" in
    up)
        if [ -z "$MIGRATION" ]; then
            echo -e "${RED}Error: Migration name required${NC}"
            usage
        fi

        MIGRATION_PATH="$MIGRATIONS_DIR/$MIGRATION"

        if [ ! -d "$MIGRATION_PATH" ]; then
            echo -e "${RED}Error: Migration directory not found: $MIGRATION_PATH${NC}"
            exit 1
        fi

        if [ ! -f "$MIGRATION_PATH/up.sql" ]; then
            echo -e "${RED}Error: up.sql not found in $MIGRATION_PATH${NC}"
            exit 1
        fi

        echo -e "${YELLOW}Applying migration: $MIGRATION${NC}"
        echo "Database: $DB_NAME@$DB_HOST"

        # Run migration
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -v ON_ERROR_STOP=1 \
            -f "$MIGRATION_PATH/up.sql"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Migration applied successfully${NC}"
        else
            echo -e "${RED}✗ Migration failed${NC}"
            exit 1
        fi
        ;;

    down)
        if [ -z "$MIGRATION" ]; then
            echo -e "${RED}Error: Migration name required${NC}"
            usage
        fi

        MIGRATION_PATH="$MIGRATIONS_DIR/$MIGRATION"

        if [ ! -d "$MIGRATION_PATH" ]; then
            echo -e "${RED}Error: Migration directory not found: $MIGRATION_PATH${NC}"
            exit 1
        fi

        if [ ! -f "$MIGRATION_PATH/down.sql" ]; then
            echo -e "${RED}Error: down.sql not found in $MIGRATION_PATH${NC}"
            exit 1
        fi

        echo -e "${YELLOW}Rolling back migration: $MIGRATION${NC}"
        echo "Database: $DB_NAME@$DB_HOST"

        # Run rollback
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -v ON_ERROR_STOP=1 \
            -f "$MIGRATION_PATH/down.sql"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Migration rolled back successfully${NC}"
        else
            echo -e "${RED}✗ Rollback failed${NC}"
            exit 1
        fi
        ;;

    status)
        echo -e "${YELLOW}Available migrations:${NC}"
        echo ""

        if [ ! -z "$(ls -A $MIGRATIONS_DIR)" ]; then
            ls -1d "$MIGRATIONS_DIR"/*/ | while read migration_dir; do
                migration_name=$(basename "$migration_dir")

                if [ -f "$migration_dir/up.sql" ]; then
                    echo -e "  ${GREEN}✓${NC} $migration_name"

                    if [ -f "$migration_dir/README.md" ]; then
                        # Show first line of README as description
                        head -1 "$migration_dir/README.md" | sed 's/^# /    Purpose: /'
                    fi
                else
                    echo -e "  ${RED}✗${NC} $migration_name (missing up.sql)"
                fi
            done
        else
            echo "  (no migrations found)"
        fi
        echo ""
        ;;

    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${NC}"
        usage
        ;;
esac
