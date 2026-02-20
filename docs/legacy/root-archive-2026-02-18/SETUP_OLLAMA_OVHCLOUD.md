# 🚀 Setup: Ollama (Local) + OVHCloud (Producción)

**Objetivo:** Configurar IA para identificación de documentos con Ollama en desarrollo y OVHCloud en producción.

**Estado:** ✅ Completamente implementado y listo para configurar

---

## 📋 Resumen de Configuración

| Entorno | Provider | Modelo | Costo | Setup |
|---------|----------|--------|-------|-------|
| **Desarrollo** | Ollama | llama3.1:8b | $0 | Local |
| **Producción** | OVHCloud | gpt-4o | Variable | Cloud |

---

## 🔧 PARTE 1: Ollama en Local (Desarrollo)

### Paso 1: Instalar Ollama

#### macOS/Linux:
```bash
curl https://ollama.ai/install.sh | sh
```

#### Windows:
1. Descargar desde: https://ollama.ai/download
2. Ejecutar instalador
3. Ollama correrá en `http://localhost:11434`

#### Verificar instalación:
```bash
ollama --version
```

---

### Paso 2: Descargar Modelo LLM

Descargar modelo recomendado (llama3.1:8b):
```bash
ollama pull llama3.1:8b
```

**Modelos disponibles (según tarea):**

```bash
# Para clasificación (rápido, eficiente)
ollama pull mistral:7b        # ~5GB

# Para análisis (más potente)
ollama pull llama3.1:70b      # ~40GB (requiere 32GB+ RAM)

# Para clasificación general
ollama pull llama3.1:8b       # ~5GB - RECOMENDADO para desarrollo

# Alternativa ligera
ollama pull neural-chat:7b    # ~4GB
```

**Comando para desarrollo (RECOMENDADO):**
```bash
ollama pull llama3.1:8b
```

---

### Paso 3: Verificar Ollama Corriendo

```bash
# Iniciar Ollama (si no está en background)
ollama serve

# En otra terminal, verificar
curl http://localhost:11434/api/tags
```

Debería retornar algo como:
```json
{
  "models": [
    {
      "name": "llama3.1:8b",
      "modified_at": "2025-02-16T...",
      "size": 5000000000
    }
  ]
}
```

---

### Paso 4: Configurar Backend para Ollama

#### Archivo: `.env` en raíz del proyecto

```bash
# =========================================
# DESARROLLO: Ollama Local
# =========================================

# AI Provider principal
AI_PROVIDER=ollama

# Configuración Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=30

# Caché de clasificaciones
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400

# Threshold de confianza
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7

# Telemetría
IMPORT_AI_LOG_TELEMETRY=true
```

---

### Paso 5: Verificar Conexión Backend ↔ Ollama

```bash
# Desde raíz del proyecto
cd apps/backend

# Instalar dependencias (si no están)
pip install -r requirements.txt

# Verificar health check
python -c "
import asyncio
from app.services.ai.factory import AIProviderFactory

async def check():
    provider = await AIProviderFactory.get_available_provider(None)
    if provider:
        health = await provider.health_check()
        print(f'✅ Provider: {provider.name}')
        print(f'✅ Health: {health}')
    else:
        print('❌ No provider available')

asyncio.run(check())
"
```

---

### Paso 6: Test de Clasificación Local

```python
# File: test_ollama_classification.py
import asyncio
from app.modules.imports.ai import get_ai_provider_singleton

async def test():
    provider = await get_ai_provider_singleton()
    
    result = await provider.classify_document(
        text="Invoice #001 Total: $100.00 Date: 2025-02-16",
        available_parsers=["csv_invoices", "products_excel"]
    )
    
    print(f"Parser: {result.suggested_parser}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Provider: {result.provider}")

asyncio.run(test())
```

---

## 🌐 PARTE 2: OVHCloud en Producción

### Paso 1: Crear Cuenta OVHCloud

1. Ir a: https://www.ovhcloud.com/
2. Crear cuenta (si no la tiene)
3. Ir a Manager: https://manager.eu.ovhcloud.com/

---

### Paso 2: Obtener Credenciales OVHCloud

#### Opción A: API Keys (Recomendado)

1. En OVHCloud Manager → **API** → **API Credentials**
2. Crear nueva aplicación:
   - **Application Name:** `gestiqcloud-ai`
   - **Description:** `AI for document classification`
3. Se generan:
   - `Application Key` (API_KEY)
   - `Application Secret` (API_SECRET)

#### Opción B: OAuth Token

1. En OVHCloud Manager → **Settings** → **Tokens**
2. Crear token con permisos:
   - `ai:*`

---

### Paso 3: Validar Acceso OVHCloud AI

```bash
# Prueba de conexión
curl -X GET \
  https://manager.eu.ovhcloud.com/api/v2/ai/health \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-OVH-Secret: YOUR_API_SECRET" \
  -H "Content-Type: application/json"
```

Respuesta esperada:
```json
{
  "status": "operational",
  "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
}
```

---

### Paso 4: Configurar Producción

#### Archivo: `.env.production` (o variables de entorno en servidor)

```bash
# =========================================
# PRODUCCIÓN: OVHCloud
# =========================================

# AI Provider
AI_PROVIDER=ovhcloud

# Credenciales OVHCloud
OVHCLOUD_API_KEY=your-api-key-here
OVHCLOUD_API_SECRET=your-api-secret-here
OVHCLOUD_BASE_URL=https://manager.eu.ovhcloud.com/api/v2
OVHCLOUD_MODEL=gpt-4o
OVHCLOUD_TIMEOUT=60

# Caché agresivo en producción
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=604800          # 7 días en producción

# Threshold más alto en producción
IMPORT_AI_CONFIDENCE_THRESHOLD=0.75

# Telemetría completa
IMPORT_AI_LOG_TELEMETRY=true

# Límites de rate-limiting
IMPORT_AI_MAX_REQUESTS_PER_MINUTE=100
```

---

### Paso 5: Desplegar en Producción

```bash
# 1. En servidor de producción
export AI_PROVIDER=ovhcloud
export OVHCLOUD_API_KEY=your-key
export OVHCLOUD_API_SECRET=your-secret

# 2. Reiniciar backend
systemctl restart gestiqcloud-backend

# O con Docker
docker restart gestiqcloud-backend

# 3. Verificar health
curl http://localhost:8000/api/v1/health
```

---

### Paso 6: Test de Clasificación en Producción

```bash
# Via HTTP
curl -X POST \
  http://localhost:8000/api/v1/imports/uploads/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@factura.xlsx"
```

Respuesta esperada:
```json
{
  "suggested_parser": "xlsx_invoice",
  "suggested_doc_type": "factura",
  "confidence": 0.95,
  "ai_enhanced": true,
  "ai_provider": "ovhcloud",
  "mapping_suggestion": {
    "Fecha": "invoice_date",
    "Concepto": "description",
    "Importe": "amount"
  }
}
```

---

## 🔄 Cambiar entre Ollama y OVHCloud

### En Desarrollo → Producción

```bash
# ANTES (desarrollo)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434

# DESPUÉS (producción)
AI_PROVIDER=ovhcloud
OVHCLOUD_API_KEY=xxx
OVHCLOUD_API_SECRET=yyy
```

### Testing de Fallback

El sistema automáticamente:
1. **Intenta OVHCloud** (si credenciales OK)
2. **Fallback a Ollama** (si OVHCloud falla)
3. **Fallback a Local** (si Ollama no está disponible)

```python
# El código automáticamente encuentra el mejor provider
result = await AIService.query(
    task=AITask.CLASSIFICATION,
    prompt="...",
    # No especificar provider = usa fallback automático
)
```

---

## 📊 Monitoreo

### Dashboard de Telemetría

```bash
# Ver métricas de IA
curl http://localhost:8000/api/v1/imports/ai/telemetry

# Respuesta:
{
  "provider": "ovhcloud",
  "requests": 1234,
  "cost": "$12.34",
  "avg_confidence": 0.92,
  "cache_hit_rate": 0.65,
  "latency_ms": 890
}
```

### Exportar Métricas

```bash
curl http://localhost:8000/api/v1/imports/ai/metrics/export \
  -H "Authorization: Bearer TOKEN" \
  > ai_metrics.csv
```

---

## 🐛 Troubleshooting

### Problema: "Ollama no disponible"

```bash
# Verificar que Ollama esté corriendo
ollama serve &

# Verificar puerto 11434
lsof -i :11434

# Reintentar
curl http://localhost:11434/api/tags
```

### Problema: "OVHCloud API error"

```bash
# Verificar credenciales
curl -X GET \
  https://manager.eu.ovhcloud.com/api/v2/ai/health \
  -H "Authorization: Bearer WRONG_KEY" \
  # Debería retornar 401

# Verificar credenciales correctas
echo "API_KEY: $OVHCLOUD_API_KEY"
echo "API_SECRET: $OVHCLOUD_API_SECRET"
```

### Problema: "Model not supported"

```bash
# Verificar modelos disponibles en Ollama
ollama list

# Verificar modelos en OVHCloud
curl -X GET \
  https://manager.eu.ovhcloud.com/api/v2/ai/models \
  -H "Authorization: Bearer YOUR_KEY"
```

### Problema: Baja confianza en clasificaciones

```bash
# Aumentar verbosidad en logs
DEBUG=app.modules.imports.ai pytest -v

# Ver decision logs
curl http://localhost:8000/api/v1/imports/uploads/analyze?debug=true
```

---

## 🚀 Performance Tips

### Para Ollama Local

```bash
# Ejecutar con GPU (si disponible)
CUDA_VISIBLE_DEVICES=0 ollama serve

# Ejecutar con más RAM asignada
ulimit -v unlimited
ollama serve
```

### Para OVHCloud

```bash
# Usar modelo más rápido para clasificación
OVHCLOUD_MODEL=gpt-3.5-turbo  # Más rápido, más barato

# Usar gpt-4o solo para análisis complejos
# Segregar por tarea
```

---

## 💰 Costos OVHCloud

| Modelo | Costo | Caso de Uso |
|--------|-------|------------|
| **gpt-3.5-turbo** | ~$0.0005/request | Clasificación rápida |
| **gpt-4-turbo** | ~$0.01/request | Análisis complejo |
| **gpt-4o** | ~$0.015/request | Mejor precisión |

**Estimación:** Si procesas 10,000 documentos/mes
- gpt-3.5-turbo: ~$5/mes
- gpt-4o: ~$150/mes

---

## ✅ Checklist Final

### Desarrollo (Ollama)

- [ ] Ollama instalado (`ollama --version`)
- [ ] Modelo descargado (`ollama list`)
- [ ] Backend en `.env`: `AI_PROVIDER=ollama`
- [ ] Ollama corriendo en http://localhost:11434
- [ ] Health check OK
- [ ] Test de clasificación funciona

### Producción (OVHCloud)

- [ ] Cuenta OVHCloud creada
- [ ] API Keys obtenidas
- [ ] Acceso a AI APIs validado
- [ ] Variables de entorno configuradas
- [ ] Backend desplegado
- [ ] Health check OK
- [ ] Test de clasificación funciona
- [ ] Monitoreo de costos habilitado

---

## 📞 Soporte

### Ollama Issues
- Docs: https://github.com/ollama/ollama
- Discord: https://discord.gg/ollama

### OVHCloud Issues
- Docs: https://docs.ovhcloud.com
- Support: https://help.ovhcloud.com

### GestiQCloud Issues
- Reportar en GitHub
- Contactar equipo técnico

---

**Autor:** Setup Documentation  
**Fecha:** 16 de Febrero 2026  
**Versión:** 1.0.0  
**Status:** ✅ Producción Ready
