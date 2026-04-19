#!/bin/bash
# GestiQ — Celery Worker Pool Manager
#
# Uso: ./ops/scripts/start_workers.sh [start|stop|restart|status]
#
# Workers gestionados:
#   celery-critical  — colas: critical,notifications,einvoicing  — concurrencia: 2
#   celery-ai        — colas: ai                                 — concurrencia: 4
#   celery-default   — colas: default,reports                    — concurrencia: 2
#
# Prerequisito: los servicios deben estar instalados con:
#   sudo cp ops/systemd/celery-*.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable celery-critical celery-ai celery-default

set -euo pipefail

SERVICES=(
    "celery-critical"
    "celery-ai"
    "celery-default"
)

ACTION="${1:-status}"

usage() {
    echo "Uso: $0 [start|stop|restart|status]"
    echo ""
    echo "  start    Inicia todos los workers"
    echo "  stop     Detiene todos los workers"
    echo "  restart  Reinicia todos los workers"
    echo "  status   Muestra estado de todos los workers"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: start/stop/restart requieren privilegios de root (sudo)." >&2
        exit 1
    fi
}

do_start() {
    check_root
    echo "==> Iniciando workers Celery..."
    for svc in "${SERVICES[@]}"; do
        echo "  Iniciando $svc..."
        systemctl start "$svc"
    done
    echo ""
    do_status
}

do_stop() {
    check_root
    echo "==> Deteniendo workers Celery..."
    for svc in "${SERVICES[@]}"; do
        echo "  Deteniendo $svc..."
        systemctl stop "$svc"
    done
    echo "Todos los workers detenidos."
}

do_restart() {
    check_root
    echo "==> Reiniciando workers Celery..."
    for svc in "${SERVICES[@]}"; do
        echo "  Reiniciando $svc..."
        systemctl restart "$svc"
    done
    echo ""
    do_status
}

do_status() {
    echo "==> Estado de workers Celery:"
    echo ""
    for svc in "${SERVICES[@]}"; do
        # systemctl is-active returns exit code 0 if active, 3 if inactive
        STATUS=$(systemctl is-active "$svc" 2>/dev/null || true)
        ENABLED=$(systemctl is-enabled "$svc" 2>/dev/null || echo "not-installed")
        printf "  %-20s  active=%-10s  enabled=%s\n" "$svc" "$STATUS" "$ENABLED"
    done
    echo ""
    echo "Para ver logs en tiempo real:"
    echo "  journalctl -u celery-critical -f"
    echo "  journalctl -u celery-ai -f"
    echo "  journalctl -u celery-default -f"
}

case "$ACTION" in
    start)   do_start ;;
    stop)    do_stop ;;
    restart) do_restart ;;
    status)  do_status ;;
    *)       usage ;;
esac
