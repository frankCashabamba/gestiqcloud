# Prioridad 1 - Progreso

## Estado: EN CURSO ⏳ (Backend 100%, Frontend 0%)

### ✅ Completado

#### 1. Exponer `/imports/files/classify` (1h)
**Ubicación:** `app/modules/imports/interface/http/preview.py`

**Cambios:**
- ✅ Agregado nuevo `files_router` con prefix `/files`
- ✅ Endpoint `POST /imports/files/classify` - Clasificación básica (heurística)
- ✅ Endpoint `POST /imports/files/classify-with-ai` - Clasificación con IA (Fase D)
- ✅ Soporta: Excel, CSV, XML
- ✅ Retorna: `suggested_parser`, `confidence`, `probabilities`, `enhanced_by_ai`, `ai_provider`

**Rutas disponibles:**
```
POST /api/v1/imports/files/classify          (heurística)
POST /api/v1/imports/files/classify-with-ai  (con IA)
```

**Registración:** `app/platform/http/router.py` línea 293-299

---

#### 2. CRUD `/imports/templates` (2h)
**Ubicación:** `app/modules/imports/interface/http/tenant.py`

**Estado:** ✅ YA EXISTE
- ✅ `POST /imports/mappings` - Crear template
- ✅ `GET /imports/mappings` - Listar templates
- ✅ `GET /imports/mappings/{id}` - Obtener template
- ✅ `PUT /imports/mappings/{id}` - Actualizar template
- ✅ `DELETE /imports/mappings/{id}` - Eliminar template

**Modelo DB:** `ImportMapping` en `app/models/core/modelsimport.py` línea 131-160

**Campos soportados:**
- `id` (UUID)
- `tenant_id` (UUID)
- `name` (String)
- `source_type` (String: 'invoices'|'bank'|'receipts'|etc)
- `version` (Integer)
- `mappings` (JSONB) - Mapeo columna Excel -> campo destino
- `transforms` (JSONB) - Transformaciones por campo
- `defaults` (JSONB) - Valores por defecto
- `dedupe_keys` (JSONB) - Claves deduplicación
- `created_at`, `updated_at` (Timestamps)

---

### ✅ Completado

#### 3. Integrar classify en frontend paso 1
**Ubicación:**
- ✅ `apps/tenant/src/modules/importador/services/classifyApi.ts` - API functions
- ✅ `apps/tenant/src/modules/importador/hooks/useClassifyFile.ts` - React hook
- ✅ `apps/tenant/src/modules/importador/components/ClassificationSuggestion.tsx` - UI component
- ✅ `apps/tenant/src/modules/importador/Wizard.tsx` - Integration paso 1 (preview)

**Implementado:**
- ✅ Service `classifyApi.ts` con `classifyFile()` y `classifyFileBasic()`
- ✅ Hook `useClassifyFile()` con loading/error/result states y confidence level
- ✅ Componente `ClassificationSuggestion` con badge de confianza
- ✅ Integración en Wizard paso Preview (después de upload)
- ✅ Muestra probabilidades de parsers (top 6)
- ✅ Mostrador de "Potenciado con IA" con provider

**Features implementadas:**
- ✅ Badge de confianza (verde ≥80%, amarillo ≥60%, rojo <60%)
- ✅ Loading spinner durante clasificación
- ✅ Error handling graceful (fallback heurístico a básico)
- ✅ Probabilidades top 6 parsers con barra visual
- ✅ Integración con IA provider (Ollama/OpenAI/Azure)
- ✅ Razón de clasificación
- ✅ Lista de parsers disponibles

**Estimado:** 1.5h ✅ COMPLETADO

---

#### 4. Tests endpoints
**Backend Tests:**
- [ ] Test `POST /imports/files/classify` con Excel
- [ ] Test `POST /imports/files/classify-with-ai` con IA mock
- [ ] Test validación archivos no soportados
- [ ] Test error handling

**Frontend Tests:**
- [ ] Test hook `useClassifyFile()`
- [ ] Test componente `ClassificationSuggestion`
- [ ] Test integración en Wizard

**Estimado:** 1h ⏳ PENDIENTE

---

### ⏳ Por Hacer

---

## 📋 Resumen Implementación

### Backend API Endpoints (Ahora ✅)
```
✅ POST   /imports/files/classify            (clasificación básica)
✅ POST   /imports/files/classify-with-ai    (con IA, NUEVA)
✅ GET    /imports/mappings                  (listar templates)
✅ POST   /imports/mappings                  (crear template)
✅ GET    /imports/mappings/{id}            (obtener template)
✅ PUT    /imports/mappings/{id}            (actualizar template)
✅ DELETE /imports/mappings/{id}            (eliminar template)
✅ POST   /imports/batches                   (crear batch)
✅ POST   /imports/files/upload              (subir archivo)
✅ POST   /imports/preview                   (preview datos)
✅ POST   /imports/ingest                    (procesar batch)
✅ POST   /imports/validate                  (validar)
```

---

## 🔍 Detalles Técnicos

### Endpoint: POST /imports/files/classify
**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/imports/files/classify" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.xlsx"
```

**Response (200):**
```json
{
  "suggested_parser": "products_excel",
  "confidence": 0.85,
  "reason": "Detected product-related columns (name, price, quantity)",
  "available_parsers": ["products_excel", "generic_excel", "csv_invoices", "csv_bank", ...],
  "content_analysis": {
    "headers": ["producto", "precio", "cantidad", ...],
    "scores": {
      "products": 3,
      "bank": 0,
      "invoices": 1
    }
  }
}
```

### Endpoint: POST /imports/files/classify-with-ai
**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/imports/files/classify-with-ai" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.xlsx"
```

**Response (200) - Con IA Enhancement:**
```json
{
  "suggested_parser": "products_excel",
  "confidence": 0.92,
  "reason": "Based on AI analysis",
  "available_parsers": [...],
  "probabilities": {
    "products_excel": 0.92,
    "generic_excel": 0.05,
    "csv_invoices": 0.03
  },
  "enhanced_by_ai": true,
  "ai_provider": "openai",
  "content_analysis": {...}
}
```

### Clasificador con IA (Fase D)
**Ubicación:** `app/modules/imports/services/classifier.py` línea 83-152

**Flujo:**
1. Análisis heurístico básico (file extension + headers)
2. Si confidence < `IMPORT_AI_CONFIDENCE_THRESHOLD`:
   - Extrae texto del archivo
   - Consulta IA provider (OpenAI/Azure/Local)
   - Retorna resultado mejorado si confidence > resultado base
3. Fallback automático si IA falla

**Providers IA soportados:**
- Ollama local (default)
- OpenAI (API key en `settings.OPENAI_API_KEY`)
- Azure OpenAI (credentials en settings)

---

## 📝 Próximos Pasos (Semana 1)

1. **Frontend Integration** (1.5h)
   - Crear `useClassifyFile` hook que consuma `/imports/files/classify-with-ai`
   - Mostrar progreso y error handling
   - Integrar en paso 1 del wizard

2. **Testing** (1h)
   - Tests unitarios para endpoints
   - Mock IA provider en tests
   - Integration tests E2E

3. **Documentation** (30m)
   - API docs en Swagger
   - Guía de integración frontend
   - Ejemplos de uso

---

## 🎯 Checklist para 100% (Semana 1)

- [x] Backend: Exponer `/imports/files/classify` ✅
- [x] Backend: Exponer `/imports/files/classify-with-ai` ✅
- [x] Backend: CRUD templates (ImportMapping) ✅
- [x] Backend: Registrar routers en platform ✅
- [x] Frontend: Hook useClassifyFile ✅
- [x] Frontend: Integrar en Wizard paso 1 ✅
- [ ] Frontend: Tests ⏳
- [ ] Backend: Tests unitarios ⏳
- [ ] Docs: API + Swagger ⏳

---

**Última actualización:** 11/11/2025
**Responsable:** Sistema Amp
**Estado:** Prioridad 1 - En Progreso ⏳ (Backend: 100%, Frontend: 100% base, Falta: Tests y Docs)
