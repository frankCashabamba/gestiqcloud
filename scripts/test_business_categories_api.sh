#!/bin/bash

# Script para testear el endpoint de Business Categories API
# PASO 1: Verificar que el endpoint funciona correctamente

echo "🧪 Testing Business Categories API"
echo "=================================="
echo ""

# Variables
BASE_URL="http://localhost:8000"
ENDPOINT="/api/v1/business-categories"

# Test 1: Listar todas las categorías
echo "✅ Test 1: GET /api/v1/business-categories"
echo "Comando:"
echo "  curl -s $BASE_URL$ENDPOINT | jq"
echo ""
echo "Respuesta esperada:"
echo "  {\"ok\": true, \"count\": 6, \"categories\": [...]}"
echo ""
curl -s "$BASE_URL$ENDPOINT" | jq
echo ""
echo ""

# Test 2: Obtener una categoría por código
echo "✅ Test 2: GET /api/v1/business-categories/retail"
echo "Comando:"
echo "  curl -s $BASE_URL$ENDPOINT/retail | jq"
echo ""
echo "Respuesta esperada:"
echo "  {\"ok\": true, \"category\": {\"code\": \"retail\", \"name\": \"Retail / Tienda\", ...}}"
echo ""
curl -s "$BASE_URL$ENDPOINT/retail" | jq
echo ""
echo ""

# Test 3: Intentar obtener una categoría que no existe
echo "✅ Test 3: GET /api/v1/business-categories/nonexistent (debe retornar 404)"
echo "Comando:"
echo "  curl -s $BASE_URL$ENDPOINT/nonexistent"
echo ""
curl -s "$BASE_URL$ENDPOINT/nonexistent" | jq
echo ""
echo ""

echo "✅ Tests completados!"
echo ""
echo "Próximos pasos:"
echo "1. Run SQL migrations: python ops/scripts/migrate_all_migrations_idempotent.py"
echo "2. Iniciar backend: python -m uvicorn app.main:app --reload"
echo "3. Ejecutar este script: bash scripts/test_business_categories_api.sh"
