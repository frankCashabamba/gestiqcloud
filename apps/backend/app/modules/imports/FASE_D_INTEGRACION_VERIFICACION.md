# Fase D - Checklist de Verificación (Integración Completada)

**Estado:** ✅ Integración lista para validar  
**Fecha:** 11 Nov 2025

---

## 1. ✅ Router Montado en main.py

**Archivo:** `app/main.py` (línea ~513)

```python
# IA Classification router (Fase D)
try:
    from app.modules.imports.ai.http_endpoints import router as ai_router
    app.include_router(ai_router, prefix="/api/v1/imports")
    _router_logger.info("IA Classification router mounted at /api/v1/imports/ai")
except Exception as e:
    _router_logger.warning(f"IA Classification router mount failed: {e}")
```

**Status:** ✅ HECHO

---

## 2. ✅ FileClassifier Integrado con IA

**Archivo:** `app/modules/imports/services/classifier.py`

**Nuevo método:** `async def classify_file_with_ai()`

Características:
- ✅ Clasificación base con heurísticas
- ✅ Extracción de texto para IA (`_extract_text()`)
- ✅ Integración con `get_ai_provider_singleton()`
- ✅ Comparación: usa IA si más confiante
- ✅ Fallback graceful si IA falla

**Status:** ✅ HECHO

---

## 3. ⏳ Configurar Variables .env

**Archivo:** `.env` en `/apps/backend/`

**Variables requeridas:** (ver `FASE_D_ENV_CONFIG.md`)

```bash
IMPORT_AI_PROVIDER=local
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=86400
IMPORT_AI_LOG_TELEMETRY=true
```

**Status:** ⏳ USUARIO (añade a `.env`)

---

## 4. Validación de Endpoints

Después de configurar `.env` y reiniciar la app, prueba:

### 4.1 Health Check
```bash
curl http://localhost:8000/api/v1/imports/ai/health
```

**Esperado:**
```json
{
  "status": "healthy",
  "provider": "local",
  "telemetry": { ... }
}
```

### 4.2 Clasificar Documento
```bash
curl -X POST http://localhost:8000/api/v1/imports/ai/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Invoice #001 Total: $100.00 Customer: ABC Tax: $10",
    "available_parsers": ["csv_invoices", "products_excel"]
  }'
```

**Esperado:**
```json
{
  "suggested_parser": "csv_invoices",
  "confidence": 0.85,
  "probabilities": { ... },
  "provider": "local"
}
```

### 4.3 Estado del Provider
```bash
curl http://localhost:8000/api/v1/imports/ai/status
```

### 4.4 Telemetría
```bash
curl http://localhost:8000/api/v1/imports/ai/telemetry
```

---

## 5. Integración con Preview (Opcional)

Si quieres usar IA en el endpoint de preview:

**Archivo:** `app/modules/imports/interface/http/preview.py`

Reemplaza:
```python
result = classifier.classify_file(tmp_path, file.filename)
```

Con:
```python
result = await classifier.classify_file_with_ai(tmp_path, file.filename)
```

**Status:** Opcional - Tests lo harán al final

---

## 6. Checklist Final de Integración

- [ ] Configurar variables en `.env` (ver paso 3)
- [ ] Reiniciar aplicación
- [ ] Verificar logs:
  ```
  [INFO] app.router: IA Classification router mounted at /api/v1/imports/ai
  [INFO] app.imports.ai.*: LocalAIProvider initialized
  ```
- [ ] Ejecutar health check (paso 4.1)
- [ ] Ejecutar test de clasificación (paso 4.2)
- [ ] Verificar status y telemetría (pasos 4.3, 4.4)

---

## 7. Problemas Comunes

| Problema | Solución |
|----------|----------|
| ImportError: get_ai_provider_singleton | Verifica que `app/modules/imports/ai/__init__.py` existe |
| IMPORT_AI_PROVIDER=local no funciona | Verifica `.env` tiene la variable |
| Endpoint 404 | Verifica que router está montado en `main.py` |
| Baja confianza local | Normal (~75-85%), considera OpenAI para producción |
| Cache no funciona | Verifica `IMPORT_AI_CACHE_ENABLED=true` |

---

## 8. Archivos Involucrados (Resumen)

### Backend (Fase D)
```
✅ app/main.py                           - Router montado
✅ app/config/settings.py                - Variables configuradas
✅ app/modules/imports/services/classifier.py - Método classify_file_with_ai()
✅ app/modules/imports/ai/               - Providers (local, openai, azure)
✅ app/modules/imports/ai/http_endpoints.py - 6 endpoints REST
```

### Configuración
```
⏳ .env                                  - Variables de entorno (usuario)
```

### Documentación
```
✅ FASE_D_ENV_CONFIG.md                  - Variables recomendadas
✅ FASE_D_INTEGRACION_VERIFICACION.md    - Este archivo
✅ FASE_D_IMPLEMENTACION_COMPLETA.md     - Documentación completa
✅ FASE_D_CHECKLIST_INTEGRACION.md       - Guía original
```

---

## Próximos Pasos Inmediatos

1. **Ahora:** Añade variables de `.env` (30 segundos)
2. **Ahora:** Reinicia la app (30 segundos)
3. **Ahora:** Ejecuta health check en curl (10 segundos)
4. **Al final:** Tests unitarios (1-2 horas)

**Duración total de integración:** ~2 minutos (sin tests)

---

**Responsables de Integración:**
- Router en main.py: ✅ Amp
- FileClassifier integrado: ✅ Amp
- Variables .env: ⏳ Usuario
- Tests: ⏳ Usuario (al final)
