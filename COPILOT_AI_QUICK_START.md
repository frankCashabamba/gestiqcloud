# ⚡ Copilot + IA - Quick Start

## ✅ Qué se Implementó

El módulo Copilot (`http://localhost:8082/kusi-panaderia/copilot`) ahora tiene **IA integrada**:

### 2 Nuevas Funciones

**1. POST `/ai/ask` con análisis inteligente**
```bash
curl -X POST http://localhost:8000/api/v1/tenant/ai/ask \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "ventas_mes",
    "with_ai_insights": true
  }'
```

**Respuesta:**
```json
{
  "cards": [{"title": "Pedidos por mes", "series": [...]}],
  "sql": "SELECT date_trunc...",
  "ai_insights": {
    "findings": ["Ventas crecieron 15%", "Marzo fue el mejor mes"],
    "trends": ["Tendencia alcista sostenida"],
    "recommendations": ["Aumentar capacidad de almacén"],
    "alerts": []
  },
  "ai_model": "llama3.1:8b"
}
```

**2. GET `/ai/suggestions` - Sugerencias contextuales**
```bash
curl -X GET http://localhost:8000/api/v1/tenant/ai/suggestions \
  -H "Authorization: Bearer TOKEN"
```

**Respuesta:**
```json
{
  "suggestions": [
    {
      "type": "inventory",
      "priority": "high",
      "content": "5 productos tienen stock bajo. Considera ordenar más de producto X",
      "action": "review_stock"
    },
    {
      "type": "sales",
      "priority": "medium",
      "content": "Oportunidad: Bundlear Pan Integral con Mantequilla",
      "action": "review_bundles"
    },
    {
      "type": "finance",
      "priority": "medium",
      "content": "Tienes 3 cobros pendientes por >$5000. Considera seguimiento",
      "action": "review_cash_flow"
    }
  ],
  "generated_at": "2025-02-21T12:30:00Z",
  "ai_enabled": true
}
```

---

## 🚀 Cómo Usar

### Local (Desarrollo con Ollama)

**1. Instalar Ollama** (si no lo tienes)
```bash
# Windows: https://ollama.ai/download/windows
# Mac: https://ollama.ai/download/mac
# Linux: https://ollama.ai/download/linux
```

**2. Descargar modelo**
```bash
ollama pull llama3.1:8b
ollama serve  # Esperar a que diga "Listening on 127.0.0.1:11434"
```

**3. Configurar .env**
```bash
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
COPILOT_TENANT_ENABLED=1
```

**4. Ejecutar backend**
```bash
cd apps/backend
python -m uvicorn app.main:app --reload
```

**5. Test endpoint**
```bash
curl -X POST http://localhost:8000/api/v1/tenant/ai/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "ventas_mes", "with_ai_insights": true}'
```

### Producción (OVHCloud)

**1. Configurar env vars en tu plataforma**
```env
AI_PROVIDER=ovhcloud
OVHCLOUD_API_KEY=your-key
OVHCLOUD_API_SECRET=your-secret
OVHCLOUD_MODEL=gpt-4o
COPILOT_TENANT_ENABLED=1
```

**2. Deploy**
```bash
git push
# (Render.com, Heroku, etc. se redeployará automáticamente)
```

---

## 📊 Topics Disponibles

Estos son los temas que se pueden analizar con IA:

| Topic | Descripción |
|-------|-------------|
| `ventas_mes` | Ventas mensuales con tendencias |
| `ventas_por_almacen` | Salidas por almacén |
| `top_productos` | Top 10 productos por importe |
| `stock_bajo` | Productos con inventario bajo |
| `pendientes_sri_sii` | Facturas electrónicas pendientes |
| `cobros_pagos` | Transacciones bancarias |

---

## 🎯 Casos de Uso

### Caso 1: Dashboard Ejecutivo
```typescript
// Frontend: Mostrar insights en dashboard
const data = await askCopilot({
  topic: 'ventas_mes',
  with_ai_insights: true
})

// Renderizar:
// - Gráfico de ventas (data.cards)
// - Hallazgos clave (data.ai_insights.findings)
// - Recomendaciones (data.ai_insights.recommendations)
```

### Caso 2: Panel de Sugerencias
```typescript
const { suggestions } = await fetchSuggestions()

// Mostrar en tarjetas con color según prioridad:
// 🔴 HIGH: Stock bajo
// 🟡 MEDIUM: Oportunidades de venta
// 🟢 LOW: Información general
```

### Caso 3: Alertas Automáticas
```typescript
// Si hay alerts, mostrar notificación
const { suggestions } = await fetchSuggestions()
suggestions
  .filter(s => s.priority === 'high')
  .forEach(alert => showNotification(alert.content))
```

---

## ⚙️ Configuración

| Variable | Desarrollo | Producción |
|----------|-----------|-----------|
| `AI_PROVIDER` | `ollama` | `ovhcloud` |
| `COPILOT_TENANT_ENABLED` | `1` | `1` |
| `COPILOT_ALLOWED_ACTIONS` | (default) | (default) |
| OLLAMA_BASE_URL | http://localhost:11434 | - |
| OVHCLOUD_API_KEY | - | (sync: false) |

---

## 🔍 Debug

### Ver logs de IA
```bash
# En .env
LOG_LEVEL=DEBUG

# Luego en logs buscar:
# "IA query (analysis): llama3.1:8b - 250ms"
```

### Test endpoint en Postman
```
POST http://localhost:8000/api/v1/tenant/ai/ask
Header: Authorization: Bearer TOKEN
Body: {
  "topic": "ventas_mes",
  "with_ai_insights": true
}
```

### Si falla IA, ¿qué pasa?
✅ **Fallback automático**: El endpoint retorna datos sin `ai_insights`
- Los datos base siempre están disponibles
- Si IA falla, devuelve lo que tenía antes (sin análisis)
- Nunca rompe la experiencia del usuario

---

## 📚 Documentación Completa

Ver: `COPILOT_AI_INTEGRATION_COMPLETE.md`

---

## 🎓 Técnico - Para Desarrolladores

### Archivos Modificados
- ✅ `apps/backend/app/modules/copilot/services.py` - Funciones async
- ✅ `apps/backend/app/modules/copilot/interface/http/tenant.py` - Endpoints
- ✅ `apps/backend/test_copilot_ai_integration.py` - Tests

### Nuevas Dependencias
- ✅ Ninguna (todas ya están en requirements.txt)

### Architecture
```
Frontend
  └─> POST /ai/ask (con_ai_insights=true)
      └─> query_readonly_enhanced()
          ├─> SQL: SELECT ... FROM sales_orders
          └─> IA: AIService.query(task=ANALYSIS, prompt=...)
              └─> Ollama/OVHCloud/OpenAI
                  └─> JSON: { findings, trends, recommendations, alerts }
```

---

**Implementado:** 21 Feb 2025  
**Pronto:** Chat conversacional (Fase 2)
