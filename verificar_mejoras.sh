#!/bin/bash
# Script de verificación de mejoras implementadas
# Ejecutar: bash verificar_mejoras.sh

set -e

echo "========================================="
echo "🔍 VERIFICACIÓN DE MEJORAS IMPLEMENTADAS"
echo "========================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} Archivo existe: $1"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}❌${NC} Archivo falta: $1"
        ((CHECKS_FAILED++))
    fi
}

check_content() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} Configurado: $3"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠️${NC}  Falta configurar: $3"
        ((CHECKS_WARNING++))
    fi
}

echo "📦 1. Verificando archivos creados..."
echo ""

check_file "apps/backend/pyproject.toml"
check_file "apps/backend/requirements-dev.txt"
check_file "apps/backend/app/core/auth_cookies.py"
check_file "apps/backend/app/middleware/endpoint_rate_limit.py"
check_file "apps/backend/app/tests/test_auth_cookies.py"
check_file "apps/backend/app/tests/test_rate_limit.py"
check_file "apps/tenant/.eslintrc.json"
check_file "apps/admin/.eslintrc.json"
check_file ".github/dependabot.yml"

echo ""
echo "🔧 2. Verificando configuraciones..."
echo ""

check_content ".pre-commit-config.yaml" "mypy" "Pre-commit: mypy"
check_content ".pre-commit-config.yaml" "bandit" "Pre-commit: bandit"
check_content "apps/backend/app/main.py" "EndpointRateLimiter" "Rate limiting por endpoint"
check_content "apps/tenant/package.json" '"lint"' "NPM script: lint (tenant)"
check_content "apps/admin/package.json" '"lint"' "NPM script: lint (admin)"
check_content "apps/tenant/vite.config.ts" "manualChunks" "Code splitting (tenant)"
check_content "apps/tenant/src/app/App.tsx" "lazy(" "Lazy loading (tenant)"

echo ""
echo "📊 3. Verificando documentación..."
echo ""

check_file "Informe_Backend.md"
check_file "Informe_Frontend.md"
check_file "RESUMEN_AUDITORIA.md"
check_file "INSTRUCCIONES_MEJORAS.md"
check_file "TAREAS_COMPLETADAS.md"
check_file "apps/backend/MIGRATION_JWT_COOKIES.md"

echo ""
echo "========================================="
echo "📊 RESUMEN DE VERIFICACIÓN"
echo "========================================="
echo -e "${GREEN}✅ Checks pasados:${NC} $CHECKS_PASSED"
echo -e "${YELLOW}⚠️  Warnings:${NC} $CHECKS_WARNING"
echo -e "${RED}❌ Checks fallidos:${NC} $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 TODAS LAS VERIFICACIONES PASARON${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "1. cd apps/backend && pip install -r requirements-dev.txt"
    echo "2. cd apps/tenant && npm install --save-dev eslint ..."
    echo "3. cd apps/admin && npm install --save-dev eslint ..."
    echo "4. pre-commit run --all-files"
    exit 0
else
    echo -e "${RED}⚠️  HAY VERIFICACIONES FALLIDAS${NC}"
    echo "Revisa los archivos marcados con ❌"
    exit 1
fi
