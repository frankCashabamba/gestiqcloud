#!/bin/bash

# Test script para FASE 2: Unidades de Medida
# Verifica que los endpoints funcionan correctamente

API_BASE="http://localhost:8000"

echo "🧪 Testing FASE 2: Unidades de Medida"
echo "======================================"
echo ""

# Test 1: Obtener unidades de un sector (panaderia)
echo "📌 Test 1: GET /api/v1/sectors/panaderia/units"
echo "Descripción: Obtener unidades de medida del sector panadería"
echo ""
curl -s "$API_BASE/api/v1/sectors/panaderia/units" | jq '.'
echo ""
echo "---"
echo ""

# Test 2: Obtener unidades de otro sector (taller)
echo "📌 Test 2: GET /api/v1/sectors/taller/units"
echo "Descripción: Obtener unidades de medida del sector taller"
echo ""
curl -s "$API_BASE/api/v1/sectors/taller/units" | jq '.'
echo ""
echo "---"
echo ""

# Test 3: Obtener configuración completa del sector
echo "📌 Test 3: GET /api/v1/sectors/panaderia/config"
echo "Descripción: Obtener configuración completa del sector (units, icons, etc.)"
echo ""
curl -s "$API_BASE/api/v1/sectors/panaderia/config" | jq '.'
echo ""
echo "---"
echo ""

# Test 4: Sector inexistente
echo "📌 Test 4: GET /api/v1/sectors/inexistente/units"
echo "Descripción: Error 404 para sector inexistente"
echo ""
curl -s -w "\nHTTP Status: %{http_code}\n" "$API_BASE/api/v1/sectors/inexistente/units" | jq '.'
echo ""
echo "---"
echo ""

echo "✅ Tests completados"
echo ""
echo "Notas:"
echo "- El servidor debe estar corriendo en http://localhost:8000"
echo "- Los endpoints cargan desde sector_templates.template_config.branding.units"
echo "- La migración 2025-11-29_001_migrate_sector_templates_to_db debe estar ejecutada"
