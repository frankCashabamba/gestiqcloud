# Guía de Integración de IA - GestiqCloud

## 📋 Resumen

Se ha implementado una **capa de abstracción centralizada de IA** que permite usar múltiples proveedores:

- **Desarrollo**: Ollama local (gratuito, privado)
- **Producción**: OVHCloud AI (gestión empresarial)
- **Fallback**: OpenAI (backup)

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│         Frontend (React)                 │
│  - Copilot, Chat, Suggestions, etc      │
└────────────────────┬────────────────────┘
                     │
        ┌────────────▼────────────┐
        │   Backend API (FastAPI) │
        │   /ai/query             │
        │   /ai/classify          │
        │   /ai/analyze           │
        └────────────┬────────────┘
                     │
        ┌────────────▼──────────────────┐
        │  AIProviderFactory (Router)   │
        │  - Selecciona proveedor       │
        │  - Maneja fallback            │
        │  - Health checks              │
        └────────────┬──────────────────┘
                     │
        ┌────────────┴──────────┬──────────────┐
        │                       │              │
    ┌───▼────┐          ┌──────▼────┐   ┌────▼─────┐
    │ Ollama │          │ OVHCloud  │   │  OpenAI  │
    │ Local  │          │ Manager   │   │   API    │
    └────────┘          └───────────┘   └──────────┘
```

## 🚀 Quick Start

### Desarrollo Local con Ollama

#### 1. Instalar Ollama
```bash
# macOS/Linux
curl https://ollama.ai/install.sh | sh

# o descarga desde https://ollama.ai
```

#### 2. Descargar modelo
```bash
ollama pull llama3.1:8b
# O para análisis más potente:
ollama pull llama3.1:70b
```

#### 3. Verificar que corre
```bash
curl http://localhost:11434/api/tags
```

#### 4. Configurar .env
```bash
ENVIRONMENT=development
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=30
OLLAMA_HEALTH_TIMEOUT=5
```

#### 5. Listo
Desde el backend, ahora todas las consultas de IA usan Ollama local.

### Producción con OVHCloud

#### 1. Configurar credenciales
```bash
ENVIRONMENT=production
OVHCLOUD_API_URL=https://manager.eu.ovhcloud.com/api/v2
OVHCLOUD_API_KEY=your_api_key_here
OVHCLOUD_API_SECRET=your_api_secret_here
OVHCLOUD_MODEL=gpt-4o
OVHCLOUD_SERVICE_NAME=ai
OVHCLOUD_TIMEOUT=60
```

#### 2. Configurar OpenAI como fallback
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

#### 3. Verificar salud
```bash
curl http://localhost:8000/api/v1/health/ai
```

## 📚 Uso en el Código

### Importar
```python
from app.services.ai import AIProviderFactory, AIService, AITask

# Inicializar factory
AIProviderFactory.initialize()
```

### Ejemplo 1: Consulta Genérica
```python
from app.services.ai import AIService, AITask

response = await AIService.query(
    task=AITask.ANALYSIS,
    prompt="Analiza estos números de ventas: ...",
    temperature=0.3,
    max_tokens=1000
)

if response.is_error:
    print(f"Error: {response.error}")
else:
    print(response.content)
    print(f"Tokens usados: {response.tokens_used}")
```

### Ejemplo 2: Clasificar Documento
```python
result = await AIService.classify_document(
    document_content="FACTURA #001...",
    expected_types=["invoice", "receipt", "order", "transfer"],
    confidence_threshold=0.7
)

print(f"Tipo: {result['type']}")
print(f"Confianza: {result['confidence']:.1%}")
print(f"Requiere revisión: {result['requires_review']}")
```

### Ejemplo 3: Generar Sugerencias
```python
suggestion = await AIService.generate_suggestion(
    context="Stock bajo de producto XYZ, tendencia de ventas creciente",
    suggestion_type="inventory"
)
print(suggestion)  # "Considerar aumentar pedido de..."
```

### Ejemplo 4: Analizar Incidencia
```python
analysis = await AIService.analyze_incident(
    incident_type="database_error",
    description="Connection timeout después de 30 segundos",
    stack_trace="...",
    additional_context={
        "module": "sales",
        "frequency": "intermittent",
        "environment": "production"
    }
)

print(f"Causa raíz: {analysis['root_cause']}")
print(f"Acciones recomendadas: {analysis['recommended_actions']}")
```

### Ejemplo 5: Generar Borrador de Documento
```python
draft = await AIService.generate_document_draft(
    document_type="invoice",
    data={
        "client_name": "Empresa XYZ",
        "items": [
            {"description": "Servicio A", "qty": 2, "unit_price": 100}
        ],
        "subtotal": 200,
        "iva": 21,
    }
)

print(f"Contenido: {draft['content']}")
print(f"Campos: {draft['fields']}")
if draft['warnings']:
    print(f"Advertencias: {draft['warnings']}")
```

## 🔌 Integración en Módulos Existentes

### 1. Copilot Mejorado
```python
# apps/backend/app/modules/copilot/services.py
from app.services.ai import AIService, AITask

async def enhance_query_with_ai(query_results: list[dict]) -> str:
    """Mejora resultados de query con análisis IA"""
    summary = json.dumps(query_results, indent=2)
    response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt=f"Resume y da insights de estos datos:\n{summary}"
    )
    return response.content
```

### 2. Clasificación de Documentos (Imports)
```python
# apps/backend/app/modules/imports/interface/http/tenant.py
from app.services.ai import AIService

result = await AIService.classify_document(
    document_content=extracted_text,
    expected_types=["invoice", "purchase_order", "receipt"],
    confidence_threshold=0.75
)

if result['requires_review']:
    # Enviar a revisión manual
    pass
else:
    # Procesar automáticamente
    process_document(result['type'])
```

### 3. Análisis de Incidencias
```python
# apps/backend/app/routers/incidents.py
from app.services.ai import AIService

analysis = await AIService.analyze_incident(
    incident_type=incident.tipo,
    description=incident.description,
    stack_trace=incident.stack_trace
)

incident.ai_analysis = analysis
db.commit()
```

### 4. Chat Inteligente (Nuevo módulo)
```python
# apps/backend/app/modules/copilot/chat.py
from app.services.ai import AIService, AITask

response = await AIService.query(
    task=AITask.CHAT,
    prompt=user_message,
    context={
        "module": current_module,
        "user_role": user_role,
        "company_data": aggregated_data
    }
)
```

### 5. Sugerencias Contextuales
```python
# apps/backend/app/modules/sales/suggestions.py
from app.services.ai import AIService

suggestion = await AIService.generate_suggestion(
    context=f"""
    Cliente: {client.name}
    Último pedido: {last_order.date}
    Patrón de compra: {buying_pattern}
    Stock disponible: {available_stock}
    """,
    suggestion_type="upsell"
)
```

## ⚙️ Configuración de Entorno

### Variables Mínimas Requeridas

#### Desarrollo
```bash
ENVIRONMENT=development
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

#### Producción
```bash
ENVIRONMENT=production
OVHCLOUD_API_KEY=...
OVHCLOUD_API_SECRET=...
OPENAI_API_KEY=...  # Fallback
```

### Variables Opcionales
```bash
# Límites y timeouts
AI_MAX_PROMPT_LENGTH=10000
OLLAMA_TIMEOUT=30
OVHCLOUD_TIMEOUT=60
OPENAI_TIMEOUT=30

# Modelo específico
OLLAMA_MODEL=llama3.1:8b
OVHCLOUD_MODEL=gpt-4o
OPENAI_MODEL=gpt-3.5-turbo
```

## 📊 Monitoreo y Debugging

### Health Check
```python
from app.services.ai import AIProviderFactory

# Revisar todos los proveedores
status = await AIProviderFactory.health_check_all()
# {'ollama': True, 'ovhcloud': False, 'openai': True}
```

### Logs
```python
import logging

# Habilitar logs detallados de IA
logging.getLogger("app.services.ai").setLevel(logging.DEBUG)
```

### Endpoint de Health
```
GET /api/v1/health/ai
```

Retorna:
```json
{
  "primary_provider": "ollama",
  "available_providers": {
    "ollama": true,
    "ovhcloud": false,
    "openai": true
  },
  "current_models": {
    "ollama": "llama3.1:8b",
    "openai": "gpt-3.5-turbo"
  }
}
```

## 🧪 Testing

### Mock Provider para Tests
```python
@pytest.fixture
async def mock_ai():
    from app.services.ai.base import AIResponse, AITask

    async def mock_call(request):
        return AIResponse(
            task=request.task,
            content="Mock response",
            model="mock",
            tokens_used=10
        )

    return mock_call

async def test_classification(mock_ai):
    result = await AIService.classify_document(
        "Test doc",
        ["type1", "type2"]
    )
    assert result['type'] in ["type1", "type2"]
```

## 🔐 Consideraciones de Seguridad

### Privacidad
- **Ollama (Desarrollo)**: Completamente local, sin datos externos
- **OVHCloud (Producción)**: Datos encriptados en tránsito, cumple GDPR
- **OpenAI (Fallback)**: Revisar políticas de privacidad antes de usar en producción

### Rate Limiting
```python
# Implementado a nivel de API
# Ver app/middleware/rate_limit.py
```

### Validación de Prompts
```python
# Sanización automática en BaseAIProvider._prepare_prompt()
- Máximo de caracteres: 10,000
- Detección de inyección SQL (futuro)
- Filtrado de datos sensibles (futuro)
```

## 📦 Dependencias Nuevas

Agregar a `requirements.txt`:
```
httpx>=0.28.1  # Ya existe
```

No se requieren nuevas dependencias pesadas.

## 🎯 Próximos Pasos

1. **Integrar en Copilot** (fase inmediata)
   - Mejorar respuestas con análisis IA
   - Agregar chat conversacional

2. **Integrar en Imports** (fase 2)
   - Reemplazar Ollama directo con factory
   - Mejorar clasificación con fallback

3. **Integrar en Incidents** (fase 2)
   - Usar nuevo AIService.analyze_incident()

4. **Nuevo módulo Chat** (fase 3)
   - Chat inteligente en todos los módulos
   - Soporte para context-aware responses

5. **Dashboard de IA** (fase 3)
   - Monitoreo de proveedores
   - Uso de tokens y costos
   - Sugerencias recientes

## 💡 Tips

- Mantén temperatura baja (0.1-0.3) para tareas determinísticas (clasificación, análisis)
- Usa temperatura media (0.5-0.7) para generación creativa
- Siempre maneja `response.is_error` para fallos graceful
- Cachea respuestas IA cuando sea posible
- Usa context para mejorar relevancia

## 📞 Soporte

Para preguntas sobre integración de IA:
1. Revisa logs en `DEBUG` level
2. Comprueba health en `/api/v1/health/ai`
3. Valida configuración en `.env`
4. Prueba con curl directamente al proveedor
