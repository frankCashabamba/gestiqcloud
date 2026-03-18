#!/usr/bin/env bash
#
# backup.sh — Automated PostgreSQL backup for GestiqCloud
#
# Usage:
#   ./backup.sh
#   DATABASE_URL=postgresql://... BACKUP_DIR=/backups BACKUP_RETAIN=14 ./backup.sh
#
# Environment variables:
#   DATABASE_URL   — PostgreSQL connection string (required; falls back to .env)
#   BACKUP_DIR     — Directory for backup files (default: /var/backups/gestiqcloud)
#   BACKUP_RETAIN  — Number of backups to keep (default: 7)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_TAG="gestiqcloud-backup"

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { echo "[$(date -u +%FT%TZ)] INFO  ${LOG_TAG}: $*"; }
log_error() { echo "[$(date -u +%FT%TZ)] ERROR ${LOG_TAG}: $*" >&2; }

# ---------------------------------------------------------------------------
# Load DATABASE_URL from environment or .env
# ---------------------------------------------------------------------------
if [ -z "${DATABASE_URL:-}" ]; then
    ENV_FILE="${SCRIPT_DIR}/../../.env"
    if [ -f "$ENV_FILE" ]; then
        # Source only DATABASE_URL to avoid side effects
        DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
        export DATABASE_URL
    fi
fi

if [ -z "${DATABASE_URL:-}" ]; then
    log_error "DATABASE_URL is not set. Provide it via environment or .env file."
    exit 1
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-/var/backups/gestiqcloud}"
BACKUP_RETAIN="${BACKUP_RETAIN:-7}"
BACKUP_FILE="${BACKUP_DIR}/gestiqcloud_${TIMESTAMP}.sql.gz"

# ---------------------------------------------------------------------------
# Ensure backup directory exists
# ---------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR"

# ---------------------------------------------------------------------------
# Run pg_dump
# ---------------------------------------------------------------------------
log_info "Starting backup → ${BACKUP_FILE}"

if pg_dump "$DATABASE_URL" --no-owner --no-acl --format=plain | gzip > "$BACKUP_FILE"; then
    FILESIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
    log_info "Backup completed successfully (${FILESIZE}): ${BACKUP_FILE}"
else
    log_error "pg_dump failed"
    rm -f "$BACKUP_FILE"
    exit 2
fi

# ---------------------------------------------------------------------------
# Rotate old backups — keep last N
# ---------------------------------------------------------------------------
BACKUP_COUNT="$(find "$BACKUP_DIR" -maxdepth 1 -name 'gestiqcloud_*.sql.gz' -type f | wc -l)"

if [ "$BACKUP_COUNT" -gt "$BACKUP_RETAIN" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - BACKUP_RETAIN))
    log_info "Rotating backups: removing ${REMOVE_COUNT} old file(s) (keeping ${BACKUP_RETAIN})"

    find "$BACKUP_DIR" -maxdepth 1 -name 'gestiqcloud_*.sql.gz' -type f -printf '%T@ %p\n' \
        | sort -n \
        | head -n "$REMOVE_COUNT" \
        | awk '{print $2}' \
        | xargs rm -f
fi

log_info "Backup rotation complete. Current backups: $(find "$BACKUP_DIR" -maxdepth 1 -name 'gestiqcloud_*.sql.gz' -type f | wc -l)"
exit 0
