# Ejemplo de Integración en app/main.py

Este archivo muestra cómo integrar los endpoints de IA en la aplicación FastAPI.

## Opción 1: Integración Simple (Recomendada)

**Añadir al archivo `app/main.py`:**

```python
# En la sección de imports
from fastapi import FastAPI
from app.modules.imports.ai.http_endpoints import router as ai_router

# ... otros imports ...

app = FastAPI(
    title="GestiqCloud API",
    version="0.1.0",
    # ... otras configuraciones ...
)

# Configurar CORS, middleware, etc.
# ... existing setup ...

# 🆕 AÑADIR ESTOS ENDPOINTS
app.include_router(ai_router)

# Otros routers...
# app.include_router(other_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Opción 2: Integración con Prefijo de Versión API

Si la app usa versionado de API:

```python
from fastapi import FastAPI, APIRouter
from app.modules.imports.ai.http_endpoints import router as ai_router

app = FastAPI()

# Crear router principal v1
api_v1 = APIRouter(prefix="/api/v1")

# Incluir el router de IA dentro de v1
api_v1.include_router(ai_router)

# Registrar todo en la app
app.include_router(api_v1)

# Ahora los endpoints serán:
# POST /api/v1/imports/ai/classify
# GET /api/v1/imports/ai/status
# etc.
```

---

## Opción 3: Integración en Estructura Modular

Si la app tiene estructura con múltiples routers por módulo:

```python
# En app/main.py
from fastapi import FastAPI
from app.modules.imports.routers import router as imports_router
from app.modules.imports.ai.http_endpoints import router as ai_router

app = FastAPI()

# Incluir routers por módulo
app.include_router(imports_router)      # Endpoints de importación existentes
app.include_router(ai_router)           # Nuevos endpoints de IA
```

---

## Verificación Post-Integración

Después de integrar, verificar que todo funciona:

```bash
# 1. Iniciar la app
cd apps/backend
python -m uvicorn app.main:app --reload

# 2. Verificar health check
curl http://localhost:8000/imports/ai/health

# 3. Verificar documentación automática
# Abrir http://localhost:8000/docs
# O http://localhost:8000/redoc
```

En la documentación de Swagger (http://localhost:8000/docs), deben aparecer:
- ✅ POST /imports/ai/classify
- ✅ GET /imports/ai/status
- ✅ GET /imports/ai/telemetry
- ✅ GET /imports/ai/metrics/export
- ✅ POST /imports/ai/metrics/validate
- ✅ GET /imports/ai/health

---

## Solución de Problemas

### Error: "ImportError: cannot import name 'router'"

**Verificar:**
1. Archivo `app/modules/imports/ai/http_endpoints.py` existe
2. El nombre en el import es correcto: `router as ai_router`

### Error: "No module named 'app.modules.imports.ai'"

**Verificar:**
1. Directorio `app/modules/imports/ai/` existe
2. Archivo `__init__.py` está presente

### Endpoints no aparecen en /docs

**Verificar:**
1. `app.include_router(ai_router)` está en el código
2. No hay rutas conflictivas
3. Reiniciar la app (Ctrl+C y ejecutar de nuevo)

### Error al ejecutar: ModuleNotFoundError

**Solución:**
```bash
# Asegurar que la ruta raíz es correcta
cd apps/backend
python -c "from app.modules.imports.ai import get_ai_provider_singleton; print('OK')"
```

---

## Configuración en Production

Para producción, asegurar:

```python
# En app/main.py o app/config/settings.py

app = FastAPI(
    docs_url="/api/docs" if not settings.is_prod else None,  # Ocultar docs en prod
    redoc_url="/api/redoc" if not settings.is_prod else None,
    openapi_url="/api/openapi.json" if not settings.is_prod else None,
)

# Configurar HTTPS
# app.add_middleware(HTTPSRedirectMiddleware)
# etc.
```

---

## Monitoreo en Production

Hacer health checks periódicos:

```bash
# Health check cada 30 segundos
watch -n 30 'curl -s http://localhost:8000/imports/ai/health | jq'

# Ver métricas
curl http://localhost:8000/imports/ai/telemetry | jq '.total_cost'
```

---

## Ejemplo Completo Mínimo

**Archivo: `app/main.py` (versión simplificada)**

```python
"""
Main FastAPI application with AI classification support (Fase D).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.modules.imports.ai.http_endpoints import router as ai_router

# Create app
app = FastAPI(
    title="GestiqCloud API",
    version="0.1.0",
)

# CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(ai_router)

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Ejecutar:**

```bash
python -m uvicorn app.main:app --reload
```

**Verificar:**

```bash
curl http://localhost:8000/imports/ai/health
curl http://localhost:8000/docs
```

---

## Próximos Pasos

1. ✅ Añadir `app.include_router(ai_router)` en `app/main.py`
2. ✅ Ejecutar `python -m uvicorn app.main:app --reload`
3. ✅ Verificar endpoints en http://localhost:8000/docs
4. ✅ Probar con curl
5. ✅ Crear tests
6. ✅ Integrar con FileClassifier (opcional)

Ver: `FASE_D_CHECKLIST_INTEGRACION.md` para pasos completos.
