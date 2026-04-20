#!/bin/bash
# GestiQ - Importador Worker Manager
#
# Uso: ./ops/scripts/start_importador_workers.sh [start|stop|restart|status]

set -euo pipefail

SERVICES=(
    "gestiq-importador-fast"
    "gestiq-importador-deep"
)

ACTION="${1:-status}"

usage() {
    echo "Uso: $0 [start|stop|restart|status]"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: start/stop/restart requieren sudo." >&2
        exit 1
    fi
}

do_start() {
    check_root
    for svc in "${SERVICES[@]}"; do
        systemctl start "$svc"
    done
    do_status
}

do_stop() {
    check_root
    for svc in "${SERVICES[@]}"; do
        systemctl stop "$svc"
    done
}

do_restart() {
    check_root
    for svc in "${SERVICES[@]}"; do
        systemctl restart "$svc"
    done
    do_status
}

do_status() {
    for svc in "${SERVICES[@]}"; do
        STATUS=$(systemctl is-active "$svc" 2>/dev/null || true)
        ENABLED=$(systemctl is-enabled "$svc" 2>/dev/null || echo "not-installed")
        printf "%-28s active=%-10s enabled=%s\n" "$svc" "$STATUS" "$ENABLED"
    done
}

case "$ACTION" in
    start)   do_start ;;
    stop)    do_stop ;;
    restart) do_restart ;;
    status)  do_status ;;
    *)       usage ;;
esac
