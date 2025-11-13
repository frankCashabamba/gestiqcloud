# Fase D - Checklist de Integración

Pasos para integrar el módulo de IA en el proyecto existente.

---

## 1. Configuración ✅ HECHO

- [x] Añadir variables a `app/config/settings.py`
- [x] Crear archivos de configuración `.env`

**Próximos pasos del usuario:**

- [ ] Verificar que `IMPORT_AI_PROVIDER=local` en `.env`
- [ ] Verificar que `IMPORT_AI_CACHE_ENABLED=true`

---

## 2. Instalación de Dependencias

### Local Provider (sin dependencias)
✅ Ya funciona sin instalar nada

### OpenAI Provider (opcional)
```bash
pip install openai>=1.0.0
```

### Azure Provider (opcional)
```bash
pip install openai>=1.0.0
```

**Checklist:**
- [ ] Ejecutar `pip install -r requirements.txt` (si está actualizado)
- [ ] O instalar manualmente: `pip install openai`

---

## 3. Integración en Router Principal

**Archivo:** `app/main.py` o donde esté el router principal

**Agregar:**

```python
# En los imports
from app.modules.imports.ai.http_endpoints import router as ai_router

# En la creación de la app (después de crear la app)
app.include_router(ai_router)
```

**Checklist:**
- [ ] Localizar archivo principal del router
- [ ] Importar `router as ai_router` de `app.modules.imports.ai.http_endpoints`
- [ ] Llamar a `app.include_router(ai_router)`
- [ ] Verificar que no hay conflictos de rutas

---

## 4. Integración con FileClassifier (Opcional)

Si se usa el clasificador de archivos existente:

**Archivo:** `app/modules/imports/services/classifier.py` o similar

**Modificar método de clasificación:**

```python
from app.modules.imports.ai import get_ai_provider_singleton
from app.config.settings import settings

class FileClassifier:
    async def classify_file_with_ai(self, file_path: str, filename: str):
        """Clasificar archivo con mejora opcional de IA."""
        
        # 1. Clasificación base (heurísticas existentes)
        base_result = self.classify_file(file_path, filename)
        
        # 2. Si confianza es baja, usar IA para mejorar
        if base_result["confidence"] < settings.IMPORT_AI_CONFIDENCE_THRESHOLD:
            try:
                # Extraer texto del archivo
                text = self._extract_text(file_path, filename)
                if not text:
                    return base_result
                
                # Obtener provider IA
                ai_provider = await get_ai_provider_singleton()
                
                # Clasificar con IA
                ai_result = await ai_provider.classify_document(
                    text=text,
                    available_parsers=list(self.parsers_info.keys()),
                    doc_metadata={"filename": filename}
                )
                
                # Si IA es más confiante, usar su resultado
                if ai_result.confidence > base_result["confidence"]:
                    return {
                        "parser_id": ai_result.suggested_parser,
                        "confidence": ai_result.confidence,
                        "probabilities": ai_result.probabilities,
                        "enhanced_by_ai": True,
                        "ai_provider": ai_result.provider,
                    }
            
            except Exception as e:
                # Fallback a clasificación base si hay error
                logger.warning(f"AI classification failed: {e}")
        
        return base_result
```

**Checklist:**
- [ ] Localizar `FileClassifier` o clase similar
- [ ] Importar `get_ai_provider_singleton` y `settings`
- [ ] Crear método `classify_file_with_ai` o similar
- [ ] Añadir lógica de mejora con threshold
- [ ] Implementar `_extract_text()` si no existe

---

## 5. Tests Unitarios

**Crear archivo:** `tests/modules/imports/ai/test_local_provider.py`

```python
import pytest
from app.modules.imports.ai.local_provider import LocalAIProvider

@pytest.mark.asyncio
async def test_classify_invoice():
    provider = LocalAIProvider()
    
    result = await provider.classify_document(
        text="Invoice #001 Total: $100.00 Customer: ABC Tax: $10",
        available_parsers=["csv_invoices", "products_excel"]
    )
    
    assert result.suggested_parser == "csv_invoices"
    assert result.confidence > 0.5

@pytest.mark.asyncio
async def test_cache():
    provider = LocalAIProvider()
    
    # Primera llamada
    result1 = await provider.classify_document(
        text="test",
        available_parsers=["csv_invoices"]
    )
    
    # Segunda llamada (debe usar caché)
    result2 = await provider.classify_document(
        text="test",
        available_parsers=["csv_invoices"]
    )
    
    assert result1.suggested_parser == result2.suggested_parser
```

**Checklist:**
- [ ] Crear directorio `tests/modules/imports/ai/`
- [ ] Crear archivo `__init__.py`
- [ ] Crear `test_local_provider.py`
- [ ] Ejecutar: `pytest tests/modules/imports/ai/ -v`
- [ ] Asegurar que todos pasen

---

## 6. Validación de Endpoints

**Ejecutar aplicación:**

```bash
cd apps/backend
python -m uvicorn app.main:app --reload
```

**Tests con curl:**

```bash
# 1. Health check
curl http://localhost:8000/imports/ai/health

# 2. Clasificar documento
curl -X POST http://localhost:8000/imports/ai/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Invoice #001 Total: $100.00",
    "available_parsers": ["csv_invoices", "products_excel"]
  }'

# 3. Ver estado
curl http://localhost:8000/imports/ai/status

# 4. Ver telemetría
curl http://localhost:8000/imports/ai/telemetry
```

**Checklist:**
- [ ] Endpoint `/imports/ai/health` retorna 200 OK
- [ ] Endpoint `/classify` retorna resultado válido
- [ ] Endpoint `/status` muestra provider actual
- [ ] Endpoint `/telemetry` lista métricas

---

## 7. Variables de Entorno

**Crear/Actualizar `.env`:**

```bash
# Requerido
ENV=development
DEBUG=true

# IA Configuration (Fase D)
IMPORT_AI_PROVIDER=local              # local | openai | azure
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7    # Usar IA si < 70%
IMPORT_AI_CACHE_ENABLED=true          # Activar caché
IMPORT_AI_CACHE_TTL=86400             # 24 horas
IMPORT_AI_LOG_TELEMETRY=true          # Registrar métricas

# Solo si usa OpenAI
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-3.5-turbo

# Solo si usa Azure
# AZURE_OPENAI_KEY=...
# AZURE_OPENAI_ENDPOINT=https://...
```

**Para Producción (.env.production):**

```bash
ENV=production

# Usar OpenAI en prod (máxima precisión)
IMPORT_AI_PROVIDER=openai
IMPORT_AI_CONFIDENCE_THRESHOLD=0.8    # Más estricto
OPENAI_API_KEY=${OPENAI_API_KEY}      # Desde secrets
OPENAI_MODEL=gpt-4                    # Mejor modelo
```

**Checklist:**
- [ ] Copiar valores a `.env`
- [ ] Verificar que `.env` no está en git
- [ ] Para producción, usar variables de entorno seguros

---

## 8. Logging

**Verificar que funciona logging:**

```bash
# Ejecutar con DEBUG
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload
```

**Debe mostrar logs como:**

```
[imports.ai.local] LocalAIProvider initialized (cache: True)
[imports.ai] Classification: csv_invoices (confidence: 0.85%, via local (22ms, $0.000000))
```

**Checklist:**
- [ ] Ver logs de inicialización del provider
- [ ] Ver logs de clasificación
- [ ] Verificar que no hay errores

---

## 9. Documentación

**Revisar:**
- [ ] `app/modules/imports/ai/README.md` - Quick start
- [ ] `FASE_D_IMPLEMENTACION_COMPLETA.md` - Documentación completa
- [ ] `example_usage.py` - Ejemplos de código

---

## 10. Performance Check

**Verificar performance:**

```python
import time
from app.modules.imports.ai import get_ai_provider_singleton

provider = await get_ai_provider_singleton()

# Medir latencia
start = time.time()
result = await provider.classify_document(
    text="Invoice #001",
    available_parsers=["csv_invoices"]
)
elapsed = (time.time() - start) * 1000

print(f"Latencia: {elapsed:.1f}ms")
```

**Valores esperados:**
- LocalAIProvider: 10-50ms
- OpenAIProvider: 500-2000ms

**Checklist:**
- [ ] Local provider: < 100ms
- [ ] Con caché: < 1ms

---

## 11. Monitoreo en Producción

**Endpoint para dashboard:**

```bash
GET /imports/ai/telemetry
```

Proporciona:
- Total requests
- Accuracy por provider
- Total cost
- Promedio latencia

**Checklist:**
- [ ] Acceder regularmente a `/telemetry`
- [ ] Monitorear costos de OpenAI
- [ ] Trackear accuracy
- [ ] Ajustar threshold si es necesario

---

## 12. Problemas Comunes

| Problema | Solución |
|----------|----------|
| ImportError: openai | `pip install openai` |
| OPENAI_API_KEY not configured | Añadir a `.env` |
| Low accuracy local | Normal (75-85%), usar OpenAI |
| Cache miss | Verificar `IMPORT_AI_CACHE_ENABLED=true` |
| Health check falla | Verificar configuración en settings |

---

## Resumen Final

| Item | Estado | Responsable |
|------|--------|-------------|
| Código IA | ✅ Hecho | Amp |
| Configuración settings | ✅ Hecho | Amp |
| HTTP Endpoints | ✅ Hecho | Amp |
| Integración Router | ⏳ Pendiente | Usuario |
| FileClassifier Integration | ⏳ Pendiente | Usuario |
| Tests | ⏳ Pendiente | Usuario |
| Variables .env | ⏳ Pendiente | Usuario |
| Validación Endpoints | ⏳ Pendiente | Usuario |
| Documentación | ✅ Hecho | Amp |

---

**Próximos pasos:**

1. Integrar router en `app/main.py`
2. Crear tests unitarios
3. Validar endpoints con curl
4. Configurar `.env`
5. Ejecutar aplicación y verificar logs

**Duración estimada:** 1-2 horas

**Soporte:** Ver `FASE_D_IMPLEMENTACION_COMPLETA.md`
