#!/bin/bash
# Test script para verificar endpoints de Copilot + IA

API_URL="http://localhost:8000/api/v1/tenant"
TOKEN="your-token-here"

echo "========================================="
echo "Testing Copilot + IA Endpoints"
echo "========================================="

# Test 1: Health check
echo -e "\n1. Verificando health check..."
curl -s -X GET "http://localhost:8000/health" | jq . || echo "❌ Backend no responde"

# Test 2: POST /ai/ask sin insights (datos puros)
echo -e "\n2. Testing /ai/ask SIN insights (datos puros)..."
curl -s -X POST "$API_URL/ai/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "ventas_mes",
    "with_ai_insights": false
  }' | jq . || echo "❌ Error en /ai/ask"

# Test 3: POST /ai/ask CON insights (con análisis IA)
echo -e "\n3. Testing /ai/ask CON insights (con análisis IA)..."
curl -s -X POST "$API_URL/ai/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "ventas_mes",
    "with_ai_insights": true
  }' | jq . || echo "❌ Error en /ai/ask con insights"

# Test 4: GET /ai/suggestions
echo -e "\n4. Testing /ai/suggestions (sugerencias)..."
curl -s -X GET "$API_URL/ai/suggestions" \
  -H "Authorization: Bearer $TOKEN" | jq . || echo "❌ Error en /ai/suggestions"

# Test 5: Otros topics
echo -e "\n5. Testing otros topics..."
for topic in "top_productos" "stock_bajo" "cobros_pagos"; do
  echo "  - Testing topic: $topic"
  curl -s -X POST "$API_URL/ai/ask" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"topic\": \"$topic\"}" | jq '.cards[0].title' || echo "  ❌ Error"
done

echo -e "\n========================================="
echo "Test complete"
echo "========================================="
