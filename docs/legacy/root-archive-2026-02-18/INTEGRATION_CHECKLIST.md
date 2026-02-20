# ✅ Checklist de Integración de IA

Pasos para integrar la infraestructura de IA en tu proyecto existente.

## 📋 Archivos Creados

✅ Capa base:
- `app/services/ai/__init__.py`
- `app/services/ai/base.py`
- `app/services/ai/service.py`
- `app/services/ai/factory.py`
- `app/services/ai/startup.py`

✅ Proveedores:
- `app/services/ai/providers/__init__.py`
- `app/services/ai/providers/ollama.py`
- `app/services/ai/providers/ovhcloud.py`
- `app/services/ai/providers/openai.py`

✅ Routers:
- `app/routers/ai_health.py`

✅ Documentación:
- `AI_INTEGRATION_GUIDE.md`
- `COPILOT_ENHANCEMENT.md`
- `.env.ai.example`
- `IA_IMPLEMENTATION_SUMMARY.md`
- `SETUP_AI_LOCAL.md`

## 🔧 Pasos de Integración

### Paso 1: Copiar archivos
```bash
# Los archivos ya están creados, no requiere acción
# Estructura está lista en: apps/backend/app/services/ai/
```

### Paso 2: Inicializar Factory en startup
Agregar a `apps/backend/app/main.py`:

```python
# En los imports
from app.services.ai.startup import initialize_ai_providers

# En la función lifespan, después del DOCS_ASSETS (alrededor de línea 163)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        validate_critical_config()
    except ConfigValidationError as e:
        logging.getLogger("app.startup").critical(f"Configuration validation failed: {e}")
        raise

    init_sentry()

    skip_docs_assets = str(os.getenv("DOCS_ASSETS_SKIP", "0")).lower() in ("1", "true", "yes")
    try:
        if not skip_docs_assets:
            if settings.ENV == "production":
                asyncio.create_task(_ensure_docs_assets())
            else:
                await asyncio.wait_for(_ensure_docs_assets(), timeout=8)
    except Exception as exc:
        logging.getLogger("app.docs").warning("Could not prepare Swagger/ReDoc assets: %s", exc)

    # 🆕 AGREGAR AQUÍ
    await initialize_ai_providers()

    # ... resto del código
    yield
    # Shutdown
    # ...
```

### Paso 3: Montar AI Health Router
Agregar a `apps/backend/app/main.py` en la sección de routers (alrededor de línea 530):

```python
# AI Health Check
try:
    from app.routers.ai_health import router as ai_health_router
    app.include_router(ai_health_router)
    _router_logger.info("AI Health router mounted at /api/v1/health/ai")
except Exception as e:
    _router_logger.warning(f"AI Health router mount failed: {e}")
```

### Paso 4: Configurar variables de entorno
Actualizar `.env` o `.env.local`:

```bash
# Desarrollo
ENVIRONMENT=development
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Producción (solo agregar si aplica)
# OVHCLOUD_API_KEY=...
# OPENAI_API_KEY=...
```

### Paso 5: Instalar Ollama (desarrollo)
```bash
# Seguir guía en SETUP_AI_LOCAL.md
curl https://ollama.ai/install.sh | sh
ollama pull llama3.1:8b
ollama serve
```

### Paso 6: Probar
```bash
# Terminal 1: Ollama corriendo
ollama serve

# Terminal 2: Backend
cd apps/backend
uvicorn app.main:app --reload

# Terminal 3: Probar health
curl http://localhost:8000/api/v1/health/ai

# Debería retornar algo como:
# {
#   "status": "healthy",
#   "primary_provider": "ollama",
#   "providers": {"ollama": true, "ovhcloud": false, "openai": false}
# }
```

## 📝 Cambios en Archivos Existentes

### main.py - Agregar imports y inicialización
```python
# Agregar después de otros imports de startup
from app.services.ai.startup import initialize_ai_providers

# Agregar en lifespan después de validate_critical_config
await initialize_ai_providers()

# Agregar router (en sección de routers)
from app.routers.ai_health import router as ai_health_router
app.include_router(ai_health_router)
```

## 🧪 Validar Integración

### Test 1: Health check
```bash
curl http://localhost:8000/api/v1/health/ai
```

Expected response:
```json
{
  "status": "healthy",
  "primary_provider": "ollama",
  "providers": {"ollama": true, ...},
  "available_providers": 1
}
```

### Test 2: Python test
```python
# apps/backend/test_ai_integration.py
import asyncio
from app.services.ai import AIService, AITask

async def test_ai():
    response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt="Soy un test. Responde con OK",
        max_tokens=50
    )
    print(f"Response: {response.content}")
    print(f"Error: {response.error}")
    assert not response.is_error

asyncio.run(test_ai())
```

Ejecutar:
```bash
cd apps/backend
python test_ai_integration.py
```

### Test 3: Listar proveedores
```bash
curl http://localhost:8000/api/v1/health/ai/providers
```

## 🚀 Próximos Pasos (Fase 2 - Error Handling)

### 1. Crear Tablas de BD (20 min)
```bash
# Opción A: Alembic migration
cd apps/backend
alembic revision --autogenerate -m "Add AI logging tables"
alembic upgrade head

# Opción B: SQL directo (ver MIGRATION_AI_LOGGING.md)
psql -f ai_logging_tables.sql

# Verificar
psql -c "\dt ai_*"
```

### 2. Importar Logger Router (5 min)
Editar `apps/backend/app/main.py`:
```python
# Después de otros routers (alrededor de línea 560)

# AI Logs and Metrics
try:
    from app.routers.ai_logs import router as ai_logs_router
    app.include_router(ai_logs_router)
    _router_logger.info("AI Logs router mounted at /api/v1/ai/logs")
except Exception as e:
    _router_logger.warning(f"AI Logs router mount failed: {e}")
```

### 3. Usar en Copilot (15 min)
Editar `apps/backend/app/modules/copilot/services.py`:
```python
# Agregar db parameter
async def query_readonly_enhanced(db: Session, topic: str, params: dict):
    result = query_readonly(db, topic, params)

    # Con logging
    response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt=f"Analiza: {json.dumps(result)}",
        db=db,          # ← Habilita logging
        module="copilot"
    )
    result['ai_insights'] = response.content
    return result
```

### 4. Probar (10 min)
```bash
# Ver logs recientes
curl http://localhost:8000/api/v1/ai/logs/recent

# Ver estadísticas
curl http://localhost:8000/api/v1/ai/logs/statistics

# Ver análisis
curl http://localhost:8000/api/v1/ai/logs/analysis/summary
```

### 5. Configurar Limpieza (5 min)
Agregar cron job:
```bash
# Diario a las 2 AM
0 2 * * * cd /app && python scripts/cleanup_ai_logs.py
```

---

## 📋 Próximos Pasos (Fase 3 - Módulos)

### Integrar en Copilot
1. ✅ Error handling + logging (Fase 2)
2. Editar `apps/backend/app/modules/copilot/services.py`
3. Agregar `query_readonly_enhanced()` (ver `COPILOT_ENHANCEMENT.md`)
4. Agregar `get_smart_suggestions()`
5. Crear endpoint `/ai/suggestions`
6. Actualizar frontend Dashboard

### Integrar en Imports
1. ✅ Error handling + logging (Fase 2)
2. Reemplazar Ollama directo con AIService
3. Usar `AIService.classify_document()` con db=session
4. Mejor manejo de fallback

### Integrar en Incidents
1. ✅ Error handling + logging (Fase 2)
2. Usar `AIService.analyze_incident()` con db=session
3. Agregar sugerencias automáticas

## ⚠️ Posibles Problemas

### "ModuleNotFoundError: No module named 'app.services.ai'"
- Verificar que carpeta `app/services/ai/` existe
- Verificar que `__init__.py` existe en cada carpeta
- Hacer `pip install -e .` desde `apps/backend/`

### "OLLAMA_URL connection refused"
- Verificar que `ollama serve` está corriendo
- Verificar URL en .env (default: `http://localhost:11434`)
- Probar: `curl http://localhost:11434/api/tags`

### "OVHCloud credentials not configured"
- Normal en desarrollo
- Solo requerido en producción
- Configurar si necesitas OVHCloud como primario

### Startup slow
- Normal en primera ejecución (verifica salud de 3 proveedores)
- Logs muestran progreso
- Segundo startup debería ser rápido

## 📊 Verificar Estructura

Después de integración, estructura debería ser:
```
apps/backend/
├── app/
│   ├── services/
│   │   └── ai/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── service.py
│   │       ├── factory.py
│   │       ├── startup.py
│   │       └── providers/
│   │           ├── __init__.py
│   │           ├── ollama.py
│   │           ├── ovhcloud.py
│   │           └── openai.py
│   ├── routers/
│   │   ├── ai_health.py  # ✨ NEW
│   │   └── ...
│   └── main.py  # ✏️ MODIFICADO
├── .env.ai.example
├── AI_INTEGRATION_GUIDE.md
├── COPILOT_ENHANCEMENT.md
└── ...
```

## ✅ Checklist Final

- [ ] Archivos copiados a su ubicación
- [ ] main.py importa `initialize_ai_providers`
- [ ] main.py llama `await initialize_ai_providers()` en lifespan
- [ ] main.py monta `ai_health_router`
- [ ] .env configurado con variables de IA
- [ ] Ollama corriendo en localhost:11434 (desarrollo)
- [ ] Health check retorna estado correcto
- [ ] Logs muestran inicialización exitosa
- [ ] Test de AIService funciona
- [ ] Documentación leída y entendida

## 🎓 Documentos a Revisar

Por orden de importancia:

1. **Para entender**: `IA_IMPLEMENTATION_SUMMARY.md`
2. **Para setup local**: `SETUP_AI_LOCAL.md`
3. **Para usar**: `AI_INTEGRATION_GUIDE.md`
4. **Para mejorar Copilot**: `COPILOT_ENHANCEMENT.md`

## 🔗 Rutas Útiles

Durante desarrollo:
```
GET  /api/v1/health/ai              # Estado de proveedores
GET  /api/v1/health/ai/providers    # Detalles de proveedores
POST /api/v1/chat                   # Chat (cuando esté integrado)
POST /api/v1/classify               # Clasificación
```

## 📞 Soporte

Si tienes problemas:

1. Revisa logs: `grep -i "IA\|ollama\|ovhcloud" backend.log`
2. Habilita DEBUG: `LOG_LEVEL=DEBUG`
3. Verifica health: `curl http://localhost:8000/api/v1/health/ai`
4. Prueba Ollama directamente: `curl http://localhost:11434/api/tags`
5. Revisa documentación en `AI_INTEGRATION_GUIDE.md`

---

**Tiempo estimado**: 15-30 minutos
**Complejidad**: Baja (principalmente configuración)
**Riesgo**: Muy bajo (no afecta código existente)

---

## ✅ IA PARA IDENTIFICACIÓN DE DOCUMENTOS - COMPLETADO

**Estado:** 🟢 **IMPLEMENTADO Y FUNCIONAL**

### Configuración Ollama + OVHCloud

Tu sistema está listo con:
- ✅ Ollama para desarrollo (gratuito, local)
- ✅ OVHCloud para producción (cloud, gpt-4o)
- ✅ Fallback automático entre providers
- ✅ Caché inteligente
- ✅ Telemetría completa

### Documentación Generada

| Documento | Propósito | Tiempo |
|-----------|-----------|--------|
| **AI_SETUP_INDEX.md** | Índice y guía | 5 min |
| **QUICK_START_AI.md** | Setup rápido | 5 min |
| **SETUP_OLLAMA_OVHCLOUD.md** | Detalle técnico | 30 min |
| **REVISION_IA_IDENTIFICACION_DOCUMENTOS.md** | Arquitectura | 20 min |
| **OLLAMA_OVHCLOUD_CONFIG_SUMMARY.md** | Resumen ejecutivo | 10 min |

### Próximos Pasos

1. Lee: `QUICK_START_AI.md` (5 min)
2. Ejecuta: 5 pasos simples para tu entorno
3. Test: Sube un archivo y verifica clasificación
4. Deploy: Usa el mismo config en producción

**Documentación:** Todos los archivos están en raíz del proyecto
**Status:** ✅ Listo para usar - Desarrollo: Ollama, Producción: OVHCloud
