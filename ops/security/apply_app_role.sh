#!/usr/bin/env bash
# Crea/actualiza el rol de aplicacion gestiq_app (NO-superuser) leyendo la
# contraseña y el nombre de BD desde el .env. Ver 01_create_app_role.sql.
#
# Uso:
#   bash ops/security/apply_app_role.sh                # usa ./.env
#   ENV_FILE=.env.production bash ops/security/apply_app_role.sh
#
# Variables del .env:
#   - SUPERUSER_URL (opcional) o DATABASE_URL: conexion superuser para crear el rol.
#   - APP_DB_PASSWORD (obligatoria): contraseña del rol gestiq_app.
# Requiere psql en el PATH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../../.env}"
SQL_FILE="$SCRIPT_DIR/01_create_app_role.sql"

[ -f "$ENV_FILE" ] || { echo "No existe el .env: $ENV_FILE" >&2; exit 1; }
[ -f "$SQL_FILE" ] || { echo "No existe el SQL: $SQL_FILE" >&2; exit 1; }

# Lee una clave del .env (toma la ultima coincidencia, quita comillas).
read_env() {
  grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'
}

SUPER_URL="$(read_env SUPERUSER_URL)"
[ -n "$SUPER_URL" ] || SUPER_URL="$(read_env DATABASE_URL)"
[ -n "$SUPER_URL" ] || { echo "No hay SUPERUSER_URL ni DATABASE_URL en $ENV_FILE" >&2; exit 1; }

APP_PW="$(read_env APP_DB_PASSWORD)"
[ -n "$APP_PW" ] || { echo "Falta APP_DB_PASSWORD en $ENV_FILE" >&2; exit 1; }

# Extrae el nombre de BD: ...://user:pass@host:port/DBNAME?params
DBNAME="${SUPER_URL##*/}"
DBNAME="${DBNAME%%\?*}"
[ -n "$DBNAME" ] || { echo "No se pudo extraer el nombre de BD de la URL" >&2; exit 1; }

echo "Aplicando rol gestiq_app sobre BD '$DBNAME' (conexion superuser)..."
psql "$SUPER_URL" -v "app_pw='$APP_PW'" -v "dbname=$DBNAME" -f "$SQL_FILE"

echo "Rol gestiq_app listo. Verifica con:"
echo "  psql \"\$SUPERUSER_URL\" -c \"SELECT rolsuper, rolbypassrls, rolcreatedb FROM pg_roles WHERE rolname='gestiq_app';\""
echo "Luego cambia DATABASE_URL/DB_DSN (backend Y workers) al rol gestiq_app."
