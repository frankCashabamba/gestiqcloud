# 🤖 Implementación Completa de IA en GestiqCloud

## 📋 Resumen Ejecutivo

Se ha implementado una **arquitectura centralizada y extensible de IA** que permite:

✅ **Desarrollo**: Usar Ollama local (gratuito, privado)  
✅ **Producción**: Usar OVHCloud AI (empresarial)  
✅ **Fallback**: OpenAI como respaldo automático  
✅ **Múltiples tareas**: Clasificación, análisis, generación, chat, sugerencias  
✅ **Sin dependencias nuevas**: Solo usa httpx (ya en requirements.txt)  

## 🏗️ Estructura Implementada

```
apps/backend/app/services/ai/
├── __init__.py                      # Exports públicos
├── base.py                          # Interface base + tipos
├── service.py                       # API unificada de alto nivel
├── factory.py                       # Factory y gestión de proveedores
└── providers/
    ├── __init__.py
    ├── ollama.py                   # Proveedor Ollama (local)
    ├── ovhcloud.py                 # Proveedor OVHCloud (producción)
    └── openai.py                   # Proveedor OpenAI (fallback)

apps/backend/app/routers/
└── ai_health.py                    # Endpoints de health check

Documentation/
├── AI_INTEGRATION_GUIDE.md         # Guía completa de uso
├── COPILOT_ENHANCEMENT.md          # Plan de mejora del Copilot
├── .env.ai.example                 # Configuración de ejemplo
└── IA_IMPLEMENTATION_SUMMARY.md    # Este archivo
```

## 🎯 Características Principales

### 1. Abstracción de Proveedores
```python
# Mismo código, diferentes proveedores
response = await AIService.query(
    task=AITask.ANALYSIS,
    prompt="Tu prompt aquí"
)
# En dev: usa Ollama local
# En prod: usa OVHCloud
# Si falla: intenta OpenAI
```

### 2. Tipos de Tareas Soportadas
- **CLASSIFICATION**: Clasificar documentos
- **ANALYSIS**: Analizar datos e incidencias
- **GENERATION**: Generar documentos (facturas, órdenes)
- **SUGGESTION**: Sugerencias contextuales
- **CHAT**: Conversación general
- **EXTRACTION**: Extracción de datos

### 3. API de Alto Nivel
```python
from app.services.ai import AIService

# Clasificar documento
result = await AIService.classify_document(content, types)

# Analizar incidencia
analysis = await AIService.analyze_incident(type, description)

# Generar sugerencias
suggestion = await AIService.generate_suggestion(context)

# Generar borrador
draft = await AIService.generate_document_draft(type, data)
```

## 🚀 Quick Start en 5 Minutos

### Desarrollo Local

1. **Instalar Ollama**
```bash
curl https://ollama.ai/install.sh | sh
ollama pull llama3.1:8b
ollama serve
```

2. **Configurar .env**
```bash
ENVIRONMENT=development
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

3. **Usar en código**
```python
from app.services.ai import AIService, AITask

response = await AIService.query(
    task=AITask.ANALYSIS,
    prompt="Analiza estos datos..."
)
```

4. **Listo** ✅

### Producción

1. **Configurar credenciales OVHCloud**
```bash
ENVIRONMENT=production
OVHCLOUD_API_KEY=xxx
OVHCLOUD_API_SECRET=xxx
OPENAI_API_KEY=xxx  # Fallback
```

2. **Health check**
```bash
curl http://api.example.com/api/v1/health/ai
```

## 📊 Integración en Módulos

### Copilot (Inmediato)
```python
# Mejorar queries con análisis IA
result = await query_readonly_enhanced(db, "ventas_mes")
# Retorna: datos + ai_insights

# Generar sugerencias automáticas
suggestions = await get_smart_suggestions(db)
```

### Imports (Fase 2)
```python
# Clasificar documentos automáticamente
result = await AIService.classify_document(text, types)
if result['requires_review']:
    send_for_manual_review()
```

### Incidents (Fase 2)
```python
# Analizar incidencias
analysis = await AIService.analyze_incident(
    incident_type, description, stack_trace
)
incident.ai_analysis = analysis
```

### Chat (Fase 3)
```python
# Conversación inteligente
response = await AIService.query(
    task=AITask.CHAT,
    prompt=user_message,
    context=module_data
)
```

## ⚙️ Configuración

### Variables Obligatorias

**Desarrollo:**
```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

**Producción:**
```bash
OVHCLOUD_API_KEY=...
OVHCLOUD_API_SECRET=...
OPENAI_API_KEY=...  # Fallback recomendado
```

### Variables Opcionales
```bash
# Límites
AI_MAX_PROMPT_LENGTH=10000
OLLAMA_TIMEOUT=30
OVHCLOUD_TIMEOUT=60

# Modelos específicos
OLLAMA_MODEL=llama3.1:8b
OVHCLOUD_MODEL=gpt-4o
OPENAI_MODEL=gpt-3.5-turbo
```

Ver: `apps/backend/.env.ai.example`

## 🔐 Seguridad

### Privacidad de Datos
- ✅ **Ollama**: Completamente local, sin datos externos
- ✅ **OVHCloud**: Encriptado, cumple GDPR
- ⚠️ **OpenAI**: Revisar términos antes de usar en producción

### Validación
- Máximo prompt: 10,000 caracteres
- Sanitización automática
- Rate limiting en endpoints (en middleware)

### Rate Limiting
```python
# Implementado en app/middleware/rate_limit.py
# Por defecto: 1000 requests/min en dev, 120 en prod
```

## 📈 Monitoreo

### Health Check
```bash
GET /api/v1/health/ai
```

Retorna:
```json
{
  "status": "healthy|degraded|unavailable",
  "primary_provider": "ollama",
  "providers": {
    "ollama": true,
    "ovhcloud": false,
    "openai": true
  }
}
```

### Logs
```python
import logging
logging.getLogger("app.services.ai").setLevel(logging.DEBUG)
```

## 💡 Ejemplos de Uso

### Ejemplo 1: Análisis de Datos
```python
response = await AIService.query(
    task=AITask.ANALYSIS,
    prompt="Analiza ventas de esta semana y genera insights",
    temperature=0.3,
    max_tokens=1000
)
print(response.content)
```

### Ejemplo 2: Clasificación
```python
result = await AIService.classify_document(
    document_content="FACTURA #001...",
    expected_types=["invoice", "receipt", "order"],
    confidence_threshold=0.75
)

if not result['requires_review']:
    process_document(result['type'])
```

### Ejemplo 3: Sugerencia
```python
suggestion = await AIService.generate_suggestion(
    context="Stock bajo, producto con tendencia creciente",
    suggestion_type="inventory"
)
print(suggestion)  # "Considerar aumentar pedido a..."
```

### Ejemplo 4: Análisis de Incidencia
```python
analysis = await AIService.analyze_incident(
    incident_type="database_error",
    description="Connection timeout",
    additional_context={"frequency": "intermittent"}
)

print(f"Causa: {analysis['root_cause']}")
print(f"Acciones: {analysis['recommended_actions']}")
```

## 📚 Documentación Completa

| Documento | Contenido |
|-----------|----------|
| `AI_INTEGRATION_GUIDE.md` | Guía completa, ejemplos, configuración |
| `COPILOT_ENHANCEMENT.md` | Plan de mejora del Copilot en 3 fases |
| `.env.ai.example` | Todas las variables de configuración |

## 🧪 Testing

### Mock Provider
```python
@pytest.mark.asyncio
async def test_ai_service():
    response = await AIService.query(
        task=AITask.CLASSIFICATION,
        prompt="Test"
    )
    assert not response.is_error
```

### Health Check
```python
from app.services.ai import AIProviderFactory

status = await AIProviderFactory.health_check_all()
# {'ollama': True, 'ovhcloud': False, 'openai': True}
```

## ✅ Checklist de Implementación

### Fase 1: Core (Completada)
- ✅ Factory pattern para proveedores
- ✅ Ollama provider (local)
- ✅ OVHCloud provider (producción)
- ✅ OpenAI provider (fallback)
- ✅ AIService unificado
- ✅ Health check endpoints
- ✅ Documentación completa

### Fase 2: Integración Copilot (Próxima)
- [ ] Integrar en query_readonly()
- [ ] Generar sugerencias automáticas
- [ ] Endpoint /suggestions
- [ ] Actualizar Dashboard
- [ ] Pruebas con Ollama

### Fase 3: Chat (Semana 2)
- [ ] Chat conversacional
- [ ] WebSocket para tiempo real
- [ ] Frontend ChatPanel
- [ ] Persistencia de conversaciones

### Fase 4: Análisis Avanzado (Semana 3)
- [ ] Predicción de tendencias
- [ ] Detección de anomalías
- [ ] Alertas inteligentes
- [ ] Exportar insights

## 🎓 Aprendizaje

### Para usar en nuevo módulo:
1. Importar `AIService`
2. Crear prompt específico de la tarea
3. Llamar `AIService.query()` con task apropiada
4. Parsear JSON si es necesario
5. Manejar `response.is_error`

### Buenas prácticas:
- Usa `temperature=0.1-0.3` para tareas determinísticas
- Usa `temperature=0.5-0.7` para creativas
- Cachea respuestas cuando sea posible
- Siempre maneja errores gracefully
- Usa contexto para mejorar relevancia
- Log en DEBUG para debugging

## 📞 Support

Para problemas:
1. Revisa `AI_INTEGRATION_GUIDE.md`
2. Comprueba health: `/api/v1/health/ai`
3. Valida .env con `.env.ai.example`
4. Habilita logs DEBUG
5. Prueba conectividad directa al proveedor

## 🎉 Conclusión

Tienes una **plataforma IA moderna y flexible** que:
- Funciona localmente en desarrollo
- Escala a producción con OVHCloud
- Falla gracefully con fallback automático
- Soporta múltiples tipos de tareas
- Es fácil de extender
- No requiere nuevas dependencias

**Siguiente paso**: Integrar en Copilot (ver `COPILOT_ENHANCEMENT.md`)

---

**Fecha**: Febrero 2025  
**Versión**: 1.0  
**Status**: ✅ Implementación Completa
