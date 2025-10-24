#!/bin/bash
# Script: Ejecutar todos los tests del sistema
# Uso: ./scripts/test_all.sh

set -e

echo "================================================"
echo "🧪 GestiQCloud - Test Suite Completo"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Backend Tests
echo -e "${BLUE}📦 Backend Tests (pytest)${NC}"
echo "----------------------------------------"
cd apps/backend
PYTHONPATH="$PWD:$PWD/apps" pytest -v \
  app/tests/test_pos_complete.py \
  app/tests/test_spec1_endpoints.py \
  app/tests/test_einvoicing.py \
  app/tests/test_integration_excel_erp.py \
  || echo -e "${RED}❌ Backend tests failed${NC}"

cd ../..
echo ""

# TPV Tests
echo -e "${BLUE}🏪 TPV Tests (vitest)${NC}"
echo "----------------------------------------"
cd apps/tpv
npm test -- --run || echo -e "${RED}❌ TPV tests failed${NC}"

cd ../..
echo ""

# Summary
echo "================================================"
echo -e "${GREEN}✅ Test Suite Completado${NC}"
echo "================================================"
echo ""
echo "Próximos pasos:"
echo "1. Revisar coverage: apps/backend/htmlcov/index.html"
echo "2. Tests E2E: Ejecutar manualmente (ver TESTING_GUIDE.md)"
echo ""
