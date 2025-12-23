#!/bin/bash

# Test script para FASE 1: Business Categories
# Verifica que los endpoints funcionan correctamente

API_BASE="http://localhost:8000"

echo "🧪 Testing FASE 1: Business Categories"
echo "======================================"
echo ""

# Test 1: Listar todas las categorías
echo "📌 Test 1: GET /api/v1/business-categories"
echo "Descripción: Listar todas las categorías de negocio activas"
curl -s "$API_BASE/api/v1/business-categories" | jq '.'
echo ""
echo "---"
echo ""

# Test 2: Obtener categoría por código (retail)
echo "📌 Test 2: GET /api/v1/business-categories/retail"
echo "Descripción: Obtener categoría específica por código"
curl -s "$API_BASE/api/v1/business-categories/retail" | jq '.'
echo ""
echo "---"
echo ""

# Test 3: Obtener categoría inexistente
echo "📌 Test 3: GET /api/v1/business-categories/nonexistent"
echo "Descripción: Error 404 para categoría inexistente"
curl -s -w "\nStatus: %{http_code}\n" "$API_BASE/api/v1/business-categories/nonexistent" | jq '.'
echo ""
echo "---"
echo ""

# Test 4: Listar configuración de tenant
echo "📌 Test 4: GET /api/v1/company/settings"
echo "Descripción: Obtener configuración consolidada del tenant"
curl -s "$API_BASE/api/v1/company/settings" \
  -H "X-Tenant-ID: test-tenant-id" | jq '.'
echo ""
echo "---"
echo ""

echo "✅ Tests completados"
echo ""
echo "Notas:"
echo "- El servidor debe estar corriendo en http://localhost:8000"
echo "- Reemplaza 'test-tenant-id' con un tenant_id real si es necesario"
echo "- Los endpoints requieren que la migración 2025-11-29_002_seed_business_categories haya sido ejecutada"
