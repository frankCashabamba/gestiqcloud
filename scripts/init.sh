#!/usr/bin/env bash
set -euo pipefail

cmd=${1:-help}

case "$cmd" in
  up)
    docker compose up -d --build ;;
  down)
    docker compose down -v ;;
  rebuild)
    docker compose build --no-cache ;;
  logs)
    svc=${2:-backend}
    docker compose logs -f "$svc" ;;
  typecheck)
    (cd apps/admin && npm ci && npm run typecheck) && \
    (cd apps/tenant && npm ci && npm run typecheck) ;;
  *)
    echo "Usage: $0 {up|down|rebuild|logs [svc]|typecheck}" ;;
esac

