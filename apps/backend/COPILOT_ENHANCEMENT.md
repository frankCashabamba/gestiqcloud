# Plan de Mejora del Copilot con IA Unificada

## 📊 Estado Actual

El módulo Copilot (apps/backend/app/modules/copilot) actualmente:
- ✅ Ejecuta queries SQL curadas
- ✅ Crea borradores de documentos
- ⚠️ NO usa IA para análisis avanzado
- ⚠️ NO interpreta datos para usuario
- ⚠️ NO genera insights

## 🚀 Mejoras Propuestas

### Fase 1: Integración Básica (Inmediata)

#### 1.1 Mejorar endpoint `/ai/ask` para devolver insights
```python
# apps/backend/app/modules/copilot/services.py

from app.services.ai import AIService, AITask
import json

async def query_readonly_enhanced(
    db: Session, 
    topic: str, 
    params: dict[str, Any],
    with_ai_insights: bool = True
) -> dict[str, Any]:
    """Query curada + análisis IA opcional"""
    
    # 1. Obtener datos (igual que ahora)
    result = query_readonly(db, topic, params)
    
    # 2. Mejorar con IA si se solicita
    if with_ai_insights and result['cards']:
        summary = json.dumps(result['cards'], indent=2)
        
        ai_response = await AIService.query(
            task=AITask.ANALYSIS,
            prompt=f"""Analiza estos datos de {topic}:
{summary}

Proporciona:
1. Resumen de hallazgos clave
2. Tendencias detectadas
3. Recomendaciones de acción
4. Alertas si hay anomalías

Responde en JSON con keys: findings, trends, recommendations, alerts"""
        )
        
        if not ai_response.is_error:
            try:
                insights = json.loads(ai_response.content)
                result['ai_insights'] = insights
            except json.JSONDecodeError:
                result['ai_insights'] = {"raw": ai_response.content}
    
    return result
```

#### 1.2 Agregar tipos específicos de sugerencias
```python
# apps/backend/app/modules/copilot/services.py

async def get_smart_suggestions(db: Session) -> list[dict[str, Any]]:
    """Genera sugerencias contextuales inteligentes"""
    
    suggestions = []
    
    # 1. Stock bajo - con sugerencia de acción
    low_stock = await query_readonly(db, "stock_bajo", {"threshold": 5})
    if low_stock['cards'][0]['data']:
        for item in low_stock['cards'][0]['data'][:3]:
            suggestion = await AIService.generate_suggestion(
                context=f"Producto {item.get('product_id')} con solo {item.get('qty')} unidades en almacén",
                suggestion_type="inventory"
            )
            if suggestion:
                suggestions.append({
                    "type": "inventory",
                    "priority": "high",
                    "content": suggestion,
                    "action": "review_stock"
                })
    
    # 2. Oportunidades de venta cruzada
    top_products = await query_readonly(db, "top_productos", {})
    if top_products['cards'][0]['data']:
        top_5 = top_products['cards'][0]['data'][:5]
        suggestion = await AIService.generate_suggestion(
            context=f"Productos más vendidos: {', '.join(p['name'] for p in top_5)}",
            suggestion_type="upsell"
        )
        if suggestion:
            suggestions.append({
                "type": "sales",
                "priority": "medium",
                "content": suggestion,
                "action": "review_bundles"
            })
    
    # 3. Patrones de cobros/pagos
    payments = await query_readonly(db, "cobros_pagos", {})
    if payments['cards'][0]['data']:
        suggestion = await AIService.generate_suggestion(
            context=f"Transacciones bancarias: {json.dumps(payments['cards'][0]['data'])}",
            suggestion_type="cash_flow"
        )
        if suggestion:
            suggestions.append({
                "type": "finance",
                "priority": "medium",
                "content": suggestion,
                "action": "review_cash_flow"
            })
    
    return suggestions
```

#### 1.3 Nuevo endpoint para sugerencias
```python
# apps/backend/app/modules/copilot/interface/http/tenant.py

class SuggestionsOut(BaseModel):
    suggestions: list[dict[str, Any]]
    generated_at: datetime

@router.get("/suggestions", response_model=SuggestionsOut)
async def ai_suggestions(db: Session = Depends(get_db)):
    """Obtiene sugerencias inteligentes generadas por IA"""
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    
    suggestions = await get_smart_suggestions(db)
    return {
        "suggestions": suggestions,
        "generated_at": datetime.utcnow()
    }
```

### Fase 2: Chat Conversacional (Semana 2)

#### 2.1 Nuevo router para chat
```python
# apps/backend/app/modules/copilot/interface/http/chat.py

from fastapi import WebSocket

class ChatMessage(BaseModel):
    content: str
    context: Optional[dict] = None

@router.post("/chat")
async def chat_query(
    message: ChatMessage,
    db: Session = Depends(get_db)
):
    """Chat inteligente sobre datos empresariales"""
    
    # 1. Enriquecer contexto con datos actuales
    context = message.context or {}
    
    # Agregar datos relevantes automáticamente
    context['top_products'] = await query_readonly(db, "top_productos", {})
    context['recent_sales'] = await query_readonly(db, "ventas_mes", {})
    
    # 2. Consultar IA con contexto
    response = await AIService.query(
        task=AITask.CHAT,
        prompt=message.content,
        context=context,
        temperature=0.5
    )
    
    return {
        "response": response.content,
        "confidence": response.confidence,
        "sources": ["sales_data", "inventory_data"],
    }

# WebSocket para chat en tiempo real
@router.websocket("/chat/ws")
async def websocket_chat(websocket: WebSocket, db: Session):
    await websocket.accept()
    
    while True:
        data = await websocket.receive_json()
        message = data.get("message", "")
        
        response = await AIService.query(
            task=AITask.CHAT,
            prompt=message,
            temperature=0.5
        )
        
        await websocket.send_json({
            "response": response.content,
            "processing_time_ms": response.processing_time_ms
        })
```

#### 2.2 Frontend - Agregar chat widget
```typescript
// apps/tenant/src/modules/copilot/ChatPanel.tsx

import { useState, useRef, useEffect } from 'react'
import { askCopilot } from './services'

export default function ChatPanel() {
  const [messages, setMessages] = useState<Array<{role: 'user'|'assistant', content: string}>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return
    
    // Agregar mensaje del usuario
    setMessages(prev => [...prev, { role: 'user', content: input }])
    setLoading(true)
    
    try {
      const response = await askCopilot({
        topic: 'chat',
        params: { message: input }
      })
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.cards[0]?.data?.response || 'Sin respuesta'
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error procesando tu pregunta'
      }])
    } finally {
      setLoading(false)
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-96">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-sm px-4 py-2 rounded-lg ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 text-gray-900'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
      </div>
      
      <div className="border-t p-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Haz una pregunta..."
          disabled={loading}
          className="flex-1 px-4 py-2 border rounded-lg"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          Enviar
        </button>
      </div>
    </div>
  )
}
```

### Fase 3: Análisis Avanzado (Semana 3)

#### 3.1 Análisis predictivo
```python
async def predictive_analysis(db: Session) -> dict[str, Any]:
    """Análisis predictivo de tendencias"""
    
    # Datos históricos
    sales_data = await query_readonly(db, "ventas_mes", {})
    
    prompt = f"""Analiza estos datos de ventas mensuales:
{json.dumps(sales_data['cards'][0]['series'])}

Proporciona análisis predictivo en JSON:
- trend: "upward"|"downward"|"stable"
- growth_rate: float (%)
- forecast_next_3_months: [float, float, float]
- confidence: float (0-1)
- recommendations: [str]"""
    
    response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt=prompt,
        temperature=0.2,
        max_tokens=1000
    )
    
    return json.loads(response.content) if not response.is_error else {}
```

#### 3.2 Alertas inteligentes
```python
async def check_anomalies(db: Session) -> list[dict]:
    """Detecta anomalías en datos"""
    
    alerts = []
    
    # Revisar stock
    low_stock = await query_readonly(db, "stock_bajo", {"threshold": 10})
    if len(low_stock['cards'][0]['data']) > 5:
        alerts.append({
            "type": "stock_alert",
            "severity": "high",
            "message": "Múltiples productos con stock bajo",
            "count": len(low_stock['cards'][0]['data'])
        })
    
    # Revisar cobros pendientes
    payments = await query_readonly(db, "cobros_pagos", {})
    pending = [p for p in payments['cards'][0]['data'] if p['estado'] == 'pending']
    if pending and sum(p['importe'] for p in pending) > 10000:
        alerts.append({
            "type": "payment_alert",
            "severity": "medium",
            "message": f"Cobros pendientes > $10,000",
            "total": sum(p['importe'] for p in pending)
        })
    
    return alerts
```

## 📝 Cambios en Frontend

### Dashboard Mejorado
```typescript
// apps/tenant/src/modules/copilot/Dashboard.tsx

import ChatPanel from './ChatPanel'
import SuggestionsPanel from './SuggestionsPanel'

export default function CopilotDashboard() {
  return (
    <div className="p-6 space-y-6">
      {/* Encabezado */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">AI Copilot</h1>
        <button onClick={loadData} className="btn-primary">
          Actualizar
        </button>
      </div>

      {/* Grid principal */}
      <div className="grid grid-cols-3 gap-6">
        {/* Datos existentes */}
        <Card title="Ventas por Mes">
          {salesMonth && /* ... */}
        </Card>
        
        {/* Chat conversacional */}
        <Card title="Chat con IA">
          <ChatPanel />
        </Card>
      </div>

      {/* Sugerencias inteligentes */}
      <SuggestionsPanel suggestions={suggestions} />
      
      {/* Alertas */}
      <AlertsPanel alerts={anomalies} />
    </div>
  )
}
```

## ✅ Checklist de Implementación

### Fase 1 (Esta semana)
- [ ] Integrar `AIService` en `copilot/services.py`
- [ ] Implementar `query_readonly_enhanced()`
- [ ] Implementar `get_smart_suggestions()`
- [ ] Agregar endpoint `/ai/suggestions`
- [ ] Actualizar Dashboard.tsx con sugerencias
- [ ] Probar con Ollama local
- [ ] Documentar en .env ejemplo

### Fase 2 (Siguiente semana)
- [ ] Implementar chat conversacional
- [ ] WebSocket para chat en tiempo real
- [ ] Frontend - ChatPanel component
- [ ] Persistencia de conversaciones
- [ ] Rate limiting para chat

### Fase 3 (Semana siguiente)
- [ ] Análisis predictivo
- [ ] Detección de anomalías
- [ ] Dashboard de alertas
- [ ] Exportar insights a PDF
- [ ] Historial de sugerencias

## 📦 Dependencias Necesarias

Todas ya están en `requirements.txt`:
- ✅ httpx (para llamadas HTTP)
- ✅ pydantic (para validación)
- ✅ sqlalchemy (para DB)

No requiere instalar nada nuevo.

## 🔐 Consideraciones

1. **Privacidad**: Los datos del usuario nunca se envían a OpenAI, solo a Ollama local (dev) u OVHCloud (prod)
2. **Performance**: Cachear sugerencias por 1 hora
3. **Costos**: Ollama es gratuito, OVHCloud cobra por API calls
4. **Fallback**: Si IA falla, mostrar datos sin análisis

## 🧪 Testing

```python
# tests/test_copilot_ai.py

import pytest
from app.services.ai import AIService, AITask

@pytest.mark.asyncio
async def test_query_enhanced():
    result = await query_readonly_enhanced(
        db=mock_db,
        topic="ventas_mes",
        with_ai_insights=True
    )
    
    assert "cards" in result
    assert "ai_insights" in result
    assert "findings" in result["ai_insights"]

@pytest.mark.asyncio
async def test_suggestions():
    suggestions = await get_smart_suggestions(mock_db)
    
    assert isinstance(suggestions, list)
    assert all("type" in s for s in suggestions)
    assert all("content" in s for s in suggestions)
```

## 📞 Soporte

Cualquier pregunta, revisar:
1. `AI_INTEGRATION_GUIDE.md` - Guía general
2. `app/services/ai/` - Implementación
3. Logs con `logging.DEBUG`
