# Fase D - IA Configurable

Módulo de clasificación de documentos con IA configurable.

## 📋 Contenido

```
ai/
├── __init__.py              # Factory + singleton
├── base.py                  # Interface AIProvider
├── local_provider.py        # IA local gratuita
├── openai_provider.py       # GPT-3.5-turbo / GPT-4
├── azure_provider.py        # Azure OpenAI
├── cache.py                 # Caché de resultados
├── telemetry.py             # Tracking de métricas
├── http_endpoints.py        # 6 REST endpoints
├── example_usage.py         # Ejemplos de uso
└── README.md                # Este archivo
```

## 🚀 Quick Start

### 1. Configuración (Local - Gratuito)

```bash
# .env
IMPORT_AI_PROVIDER=local
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400
```

### 2. Usar en Código

```python
from app.modules.imports.ai import get_ai_provider_singleton

# Clasificar documento
provider = await get_ai_provider_singleton()

result = await provider.classify_document(
    text="Invoice #001 Total: $100.00",
    available_parsers=["csv_invoices", "products_excel"]
)

print(result.suggested_parser)  # csv_invoices
print(result.confidence)         # 0.85
```

### 3. HTTP API

```bash
# Clasificar
curl -X POST http://localhost:8000/imports/ai/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Invoice #001",
    "available_parsers": ["csv_invoices", "products_excel"]
  }'

# Ver estado
curl http://localhost:8000/imports/ai/status

# Ver métricas
curl http://localhost:8000/imports/ai/telemetry
```

## 🎯 Providers Disponibles

### LocalAIProvider (Gratuito)
- **Latencia:** 10-50ms
- **Precisión:** 75-85%
- **Costo:** $0.00
- **Dependencias:** Ninguna

```bash
IMPORT_AI_PROVIDER=local
```

### OpenAIProvider (Pago)
- **Latencia:** 500-2000ms
- **Precisión:** 95%+
- **Costo:** $0.0005-0.015 por request
- **Dependencias:** `pip install openai`

```bash
IMPORT_AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

### AzureOpenAIProvider (Pago)
- **Latencia:** 500-2000ms
- **Precisión:** 95%+
- **Costo:** Variable según tier
- **Dependencias:** `pip install openai`

```bash
IMPORT_AI_PROVIDER=azure
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
```

## 📊 HTTP Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/imports/ai/classify` | Clasificar documento |
| GET | `/imports/ai/status` | Estado del provider |
| GET | `/imports/ai/telemetry` | Métricas agregadas |
| GET | `/imports/ai/metrics/export` | Exportar detalles |
| POST | `/imports/ai/metrics/validate` | Validar clasificación |
| GET | `/imports/ai/health` | Health check |

## 🔧 Configuración Avanzada

### Threshold de Confianza

Si la confianza está por debajo del threshold, se usa IA para mejorar:

```bash
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7  # Usa IA si < 70%
```

### Caché

Mejora performance evitando re-clasificar documentos iguales:

```bash
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400           # 24 horas
```

### Telemetría

Registra métricas para análisis de precisión y costos:

```bash
IMPORT_AI_LOG_TELEMETRY=true
```

## 📈 Monitoreo

### Ver Stats del Provider

```python
provider = await get_ai_provider_singleton()
stats = provider.get_telemetry()

print(f"Requests: {stats['requests']}")
print(f"Cost: ${stats['total_cost']}")
print(f"Avg confidence: {stats['avg_confidence']:.0%}")
```

### Exportar Métricas

```python
from app.modules.imports.ai.telemetry import telemetry

metrics = telemetry.export_metrics(provider="openai")
# Guardar en CSV/JSON para análisis
```

### Calcular Precisión

```python
# Después de validar clasificaciones
accuracy = telemetry.get_accuracy()
print(f"Accuracy: {accuracy:.0%}")

accuracy_openai = telemetry.get_accuracy(provider="openai")
print(f"OpenAI Accuracy: {accuracy_openai:.0%}")
```

## 🧪 Tests

```bash
# Tests unitarios
pytest tests/modules/imports/ai/

# Test local provider
pytest tests/modules/imports/ai/test_local_provider.py -v

# Test con cobertura
pytest tests/modules/imports/ai/ --cov
```

## 🐛 Troubleshooting

### Error: "OpenAI provider requires 'openai' package"

```bash
pip install openai
```

### Error: "OPENAI_API_KEY not configured"

Añadir a `.env`:
```bash
OPENAI_API_KEY=sk-xxx...
```

### Cache no funciona

Verificar:
```bash
IMPORT_AI_CACHE_ENABLED=true
```

### Baja precisión local

Es normal (75-85%). Opciones:
1. Usar OpenAI para mayor precisión
2. Proporcionar más contexto en el texto
3. Ajustar patterns en `LocalAIProvider.DOC_PATTERNS`

## 📚 Documentación Completa

Ver: `FASE_D_IMPLEMENTACION_COMPLETA.md`

## 🔜 Roadmap

- [ ] Fine-tuning modelo local
- [ ] Vector database (Pinecone)
- [ ] A/B testing de providers
- [ ] Feedback loop automático
- [ ] Multi-language support
- [ ] Dashboard en tiempo real
- [ ] Batch processing API

## 📝 Ejemplos

Ver: `example_usage.py`

```bash
# Ejecutar ejemplos
python -m app.modules.imports.ai.example_usage
```

## 🤝 Contribuir

1. Añadir nuevos patterns en `LocalAIProvider.DOC_PATTERNS`
2. Crear tests en `tests/modules/imports/ai/`
3. Documentar cambios en README

## 📞 Soporte

- Issue: Reportar en GitHub
- Discussion: Usar discussions del proyecto
- Docs: Ver FASE_D_IMPLEMENTACION_COMPLETA.md
