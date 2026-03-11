# ⚡ REFERENCIA RÁPIDA - GestiqCloud IA

## 🚀 Inicio Rápido (10 min)

```bash
# 1. Instalar Ollama
curl https://ollama.ai/install.sh | sh
ollama pull llama3.1:8b
ollama serve

# 2. Configurar
echo "OLLAMA_URL=http://localhost:11434" >> apps/backend/.env

# 3. Crear tablas
python ops/scripts/migrate_all_migrations_idempotent.py

# 4. Usar
curl http://localhost:8000/api/v1/health/ai
```

---

## 💻 Uso en Código

### Simple (sin logging)
```python
response = await AIService.query(
    task=AITask.ANALYSIS,
    prompt="Tu pregunta aquí"
)
```

### Con logging (recomendado)
```python
response = await AIService.query(
    task=AITask.ANALYSIS,
    prompt="Tu pregunta aquí",
    db=session,
    module="copilot"
)
```

### Con todas las opciones
```python
response = await AIService.query(
    task=AITask.CLASSIFICATION,
    prompt="Clasifica: ...",
    temperature=0.3,
    max_tokens=500,
    db=session,
    module="imports",
    user_id=user.id,
    enable_recovery=True
)
```

---

## 📊 Endpoints de Logs

```bash
# Logs recientes
curl http://localhost:8000/api/v1/ai/logs/recent?limit=20

# Estadísticas
curl http://localhost:8000/api/v1/ai/logs/statistics?hours=24

# Performance de proveedores
curl http://localhost:8000/api/v1/ai/logs/providers

# Top errores
curl http://localhost:8000/api/v1/ai/logs/errors/top

# Análisis completo
curl http://localhost:8000/api/v1/ai/logs/analysis/summary

# Sugerencias de fix
curl -X POST "http://localhost:8000/api/v1/ai/logs/errors/TIMEOUT/fix?error_message=timeout"
```

---

## 🎯 Tipos de Tareas

```python
from app.services.ai import AITask

AITask.CLASSIFICATION    # Clasificar documentos
AITask.ANALYSIS         # Analizar datos
AITask.GENERATION       # Generar documentos
AITask.SUGGESTION       # Sugerencias
AITask.CHAT            # Conversación
AITask.EXTRACTION      # Extracción de datos
```

---

## 📁 Archivos Importantes

| Archivo | Para... |
|---------|---------|
| IA_IMPLEMENTATION_SUMMARY.md | Entender qué es |
| SETUP_AI_LOCAL.md | Setup Ollama |
| AI_INTEGRATION_GUIDE.md | Ejemplos de uso |
| ERROR_HANDLING_AND_RECOVERY.md | Logging y recovery |
| INTEGRATION_CHECKLIST.md | Pasos de integración |

---

## 🔍 Debugging

```bash
# Ver si Ollama está corriendo
curl http://localhost:11434/api/tags

# Health check de IA
curl http://localhost:8000/api/v1/health/ai

# Ver logs con debug
LOG_LEVEL=DEBUG uvicorn app.main:app

# Ver logs recientes
curl http://localhost:8000/api/v1/ai/logs/recent?limit=5
```

---

## ⚙️ Configuración Básica

```bash
# Desarrollo
ENVIRONMENT=development
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Producción
ENVIRONMENT=production
OVHCLOUD_API_KEY=xxx
OVHCLOUD_API_SECRET=xxx
OPENAI_API_KEY=xxx
```

---

## 🆘 Problemas Comunes

| Problema | Solución |
|----------|----------|
| "Connection refused" | Verificar `ollama serve` corre |
| "No providers available" | Verificar OLLAMA_URL en .env |
| "Table does not exist" | Run `python ops/scripts/migrate_all_migrations_idempotent.py` |
| "ImportError ai_logs" | Verificar routers importados en main.py |
| "Slow responses" | Usar modelo más pequeño (mistral:7b) |

---

## 📈 Métricas Clave

```bash
# Error rate últimas 24h
curl "http://localhost:8000/api/v1/ai/logs/statistics?hours=24"
# → Buscar "error_rate"

# Proveedor más rápido
curl "http://localhost:8000/api/v1/ai/logs/providers?hours=24"
# → Buscar "avg_time_ms" más bajo

# Requests más lentos
curl "http://localhost:8000/api/v1/ai/logs/requests/slow?limit=5"
```

---

## 🔄 Estrategias de Recuperación

1. **RetryStrategy** - Reintenta 2-3 veces con backoff
2. **SimplifyStrategy** - Reduce prompt si es muy largo
3. **FallbackStrategy** - Cambia a otro proveedor
4. **CacheStrategy** - (futuro) Usa caché

Automáticas cuando `enable_recovery=True` (por defecto)

---

## 📦 Estructura de Directorios

```
apps/backend/app/
├── services/ai/              # ← Nuevo módulo IA
│   ├── base.py              # Interfaces
│   ├── service.py           # API unificada
│   ├── factory.py           # Factory
│   ├── logging.py           # Logger
│   ├── recovery.py          # Recuperación
│   └── providers/           # Proveedores
├── models/
│   └── ai_log.py            # ← Modelos BD
├── routers/
│   ├── ai_health.py         # ← Health checks
│   └── ai_logs.py           # ← Endpoints logs
```

---

## ✅ Checklist Rápido

```
Setup:
  [ ] Ollama instalado y corriendo
  [ ] .env configurado
  [ ] Tablas BD creadas
  [ ] Routers importados

Uso:
  [ ] Pasado db=session a AIService.query()
  [ ] Health check funciona
  [ ] Logs se crean en BD

Integración:
  [ ] Copilot integrado
  [ ] Tests funcionando
  [ ] Logs se ven en /api/v1/ai/logs
```

---

## 🎓 Ejemplos Prácticos

### Clasificar documento
```python
result = await AIService.classify_document(
    document_content="FACTURA #001...",
    expected_types=["invoice", "order", "receipt"],
    confidence_threshold=0.75
)
print(f"Tipo: {result['type']}, Confianza: {result['confidence']:.1%}")
```

### Analizar incidencia
```python
analysis = await AIService.analyze_incident(
    incident_type="database_error",
    description="Connection timeout",
    additional_context={"frequency": "intermittent"}
)
print(f"Causa: {analysis['root_cause']}")
print(f"Acciones: {analysis['recommended_actions']}")
```

### Generar sugerencia
```python
suggestion = await AIService.generate_suggestion(
    context="Stock bajo de producto XYZ",
    suggestion_type="inventory"
)
print(suggestion)
```

---

## 🔗 Links Rápidos

- Ollama: https://ollama.ai
- OVHCloud AI: https://manager.eu.ovhcloud.com
- OpenAI: https://api.openai.com
- Documentación completa: Revisar archivos .md en raíz

---

## 📞 Soporte

- **Instalación**: SETUP_AI_LOCAL.md
- **Integración**: INTEGRATION_CHECKLIST.md
- **Uso**: AI_INTEGRATION_GUIDE.md
- **Errores**: ERROR_HANDLING_AND_RECOVERY.md
- **Tablas**: MIGRATION_AI_LOGGING.md

---

**¡Listo para empezar!** 🚀
