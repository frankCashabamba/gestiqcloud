# Fase D - Variables de Entorno (Integración Completa)

## Configuración Requerida

Añade las siguientes variables a tu archivo `.env` en `/apps/backend/.env`:

```bash
# ========================================
# Fase D: IA Configurable (REQUERIDO)
# ========================================

# Provider de IA: local (gratuito) | openai (pago) | azure (pago)
IMPORT_AI_PROVIDER=local

# Threshold de confianza para usar IA
# Si confidence < 0.7, mejora con IA
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7

# Activar caché de clasificaciones
IMPORT_AI_CACHE_ENABLED=true

# TTL de caché (segundos, default 24 horas)
IMPORT_AI_CACHE_TTL=86400

# Registrar telemetría de IA
IMPORT_AI_LOG_TELEMETRY=true

# ========================================
# SOLO SI USAS OpenAI (OPCIONAL)
# ========================================
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-3.5-turbo

# ========================================
# SOLO SI USAS Azure (OPCIONAL)
# ========================================
# AZURE_OPENAI_KEY=...
# AZURE_OPENAI_ENDPOINT=https://...openai.azure.com/
```

---

## Configuraciones Recomendadas por Entorno

### Development (Local - Gratuito)
```bash
IMPORT_AI_PROVIDER=local
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400
IMPORT_AI_LOG_TELEMETRY=true
```

### Production (OpenAI - Máxima Precisión)
```bash
IMPORT_AI_PROVIDER=openai
IMPORT_AI_CONFIDENCE_THRESHOLD=0.8
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL=gpt-4
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400
IMPORT_AI_LOG_TELEMETRY=true
```

---

## Performance Esperado

### LocalAIProvider (Gratuito)
- Latencia: 10-50ms
- Precisión: 75-85%
- Costo: $0.00
- Cache hit rate: 65-75%

### OpenAIProvider (Pago)
- Latencia: 500-2000ms
- Precisión: 95%+
- Costo: $0.0005-0.015/request
- Cache hit rate: 60-70%

---

## Pasos de Integración

1. ✅ **Router montado** en `app/main.py` - endpoints `/api/v1/imports/ai/*`
2. ✅ **FileClassifier integrado** en `app/modules/imports/services/classifier.py` - método `classify_file_with_ai()`
3. ⏳ **Variables .env** - Añade las variables arriba a tu `.env`
4. ⏳ **Validar endpoints** - Ejecuta tests (al final)

---

## Endpoints Disponibles (después de integrar)

```bash
# Health check
GET /api/v1/imports/ai/health

# Clasificar documento
POST /api/v1/imports/ai/classify
  {
    "text": "Invoice #001 Total: $100.00",
    "available_parsers": ["csv_invoices", "products_excel"]
  }

# Estado del provider
GET /api/v1/imports/ai/status

# Telemetría
GET /api/v1/imports/ai/telemetry

# Exportar métricas
GET /api/v1/imports/ai/metrics/export

# Validar clasificación
POST /api/v1/imports/ai/metrics/validate
```

---

## Próximos Pasos

1. Añade las variables de `.env` recomendadas arriba
2. Inicia la aplicación: `python -m uvicorn app.main:app --reload`
3. Verifica que el router está montado (logs debe mostrar):
   ```
   [INFO] app.router: IA Classification router mounted at /api/v1/imports/ai
   ```
4. Tests al final (cuando solicites)
