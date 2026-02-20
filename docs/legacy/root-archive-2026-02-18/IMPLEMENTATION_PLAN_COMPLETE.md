# 🚀 Plan Completo de Implementación: Importer + IA

**Fecha:** 16 Febrero 2026
**Estado Actual:** 95% Frontend, 90% Backend
**Objetivo:** 100% Implementado y Funcional

---

## 📊 Estado Actual del Sistema

### ✅ YA IMPLEMENTADO

#### Frontend (95%)
- ✅ Wizard de 6 pasos (upload, preview, mapping, validate, summary, importing)
- ✅ Componentes principales: MapeoCampos, VistaPreviaTabla, ResumenImportacion
- ✅ Servicios IA: classifyApi.ts, analyzeApi.ts
- ✅ Hooks: useImportProgress, useClassifyFile, useAnalyzeFile
- ✅ Context: ImportQueueContext
- ✅ Soporte OCR y carga chunked
- ✅ Interfaz de plantillas
- ✅ Mapeo automático con Levenshtein

#### Backend (90%)
- ✅ 7 Endpoints HTTP operacionales
- ✅ Servicios de análisis y clasificación
- ✅ IA Providers: Ollama, OVHCloud, OpenAI, Azure, Local
- ✅ Validadores y parsers
- ✅ OCR service integrado
- ✅ Smart router para detección de tipos
- ✅ Caché inteligente
- ✅ Telemetría completa

---

## ⚠️ LO QUE FALTA (5-10%)

### Frontend - Mejoras Recomendadas

| Item | Prioridad | Esfuerzo | Estado |
|------|-----------|----------|--------|
| Integración OAuth2 en login | Alta | 4h | TODO |
| Error boundaries en componentes | Alta | 2h | TODO |
| Tests E2E con Playwright | Media | 6h | TODO |
| Soporte offline (ElectricSQL) | Media | 8h | TODO |
| Dark mode completo | Baja | 3h | TODO |
| Perfeccionamiento UI/UX | Baja | 4h | TODO |

### Backend - Mejoras Recomendadas

| Item | Prioridad | Esfuerzo | Estado |
|------|-----------|----------|--------|
| Validación de esquema Pydantic | Alta | 2h | TODO |
| Rate limiting por tenant | Alta | 3h | TODO |
| Métricas Prometheus | Media | 4h | TODO |
| Healthcheck completo | Media | 2h | TODO |
| Logging estructurado | Media | 3h | TODO |
| Sincronización caché Redis | Media | 4h | TODO |

---

## 🎯 Implementación Inmediata (Hoy)

### 1. Frontend - Completar Integración IA

#### Archivo: `apps/tenant/src/modules/importer/components/ClassificationSuggestion.tsx`

**Status:** ✅ Existe pero necesita validación

**Qué falta:**
- Error handling mejorado
- Loading states claros
- Fallback UI si IA falla

#### Archivo: `apps/tenant/src/modules/importer/hooks/useClassifyFile.ts`

**Status:** ✅ Existe y está funcional

**Qué hay:**
- Hook completo para clasificación
- Manejo de errores
- Cache de resultados
- Fallback a local

#### Archivo: `apps/tenant/src/modules/importer/hooks/useAnalyzeFile.ts`

**Status:** ⚠️ Necesita actualización

**Qué falta:**
- Integración con nuevo endpoint `/imports/uploads/analyze`
- Manejo de `ai_provider` en respuesta
- Display de confianza y provider usado

#### Archivo: `apps/tenant/src/modules/importer/components/AIProviderSettings.tsx`

**Status:** ❓ Verificar si existe

**Qué se necesita:**
- Selector de provider (ollama vs ovhcloud)
- Display de proveedor activo
- Indicador de latencia
- Fallback visual

---

### 2. Backend - Endpoints Faltantes

#### Endpoint: POST `/imports/ai/health`

**Status:** ⚠️ Existe pero no bien integrado

**Implementación:**
```python
@router.get("/health")
async def ai_health(request: Request):
    """Healthcheck del provider IA actual"""
    claims = get_access_claims(request)

    # Obtener provider actual
    provider = await AIProviderFactory.get_available_provider()

    if not provider:
        return {"status": "degraded", "provider": None}

    is_healthy = await provider.health_check()

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "provider": provider.name,
        "available_providers": [p.name for p in get_all_providers()],
        "latency_ms": measure_latency(provider)
    }
```

#### Endpoint: GET `/imports/ai/telemetry`

**Status:** ✅ Implementado

**Verificación necesaria:** Que retorna costos correctos por provider

#### Endpoint: POST `/imports/files/classify`

**Status:** ✅ Implementado en classifyApi

**Verificación necesaria:** Que acepta file upload y retorna ClassifyResponse

---

### 3. Integración Completa Frontend ↔ Backend

#### Actualizar: `apps/tenant/src/modules/importer/Wizard.tsx`

**Cambios necesarios:**

1. **Después de subir archivo → Usar analyzeApi en lugar de classifyApi**
```typescript
// ANTES
const classification = await classify(file)

// DESPUÉS
const analysis = await analyzeFile(file)
const { suggested_parser, mapping_suggestion, ai_enhanced, ai_provider } = analysis
```

2. **Mostrar ai_provider en UI**
```typescript
{analysis.ai_enhanced && (
  <div className="text-sm text-gray-600">
    Mejorado con IA ({analysis.ai_provider})
  </div>
)}
```

3. **Guardar ai_provider en batchId**
```typescript
await confirmBatch({
  batchId,
  parserChoice: suggested_parser,
  mapeoManual: mapa,
  aiProvider: ai_provider,  // NUEVO
  aiConfidence: confidence,  // NUEVO
})
```

---

### 4. Componentes Nuevos Necesarios

#### `apps/tenant/src/modules/importer/components/AIProviderBadge.tsx`

```typescript
import React from 'react'

interface AIProviderBadgeProps {
  provider?: string
  confidence?: number
  enhanced: boolean
}

export function AIProviderBadge({
  provider,
  confidence = 0,
  enhanced
}: AIProviderBadgeProps) {
  if (!enhanced || !provider) return null

  const colorMap: Record<string, string> = {
    ollama: 'bg-blue-100 text-blue-700',
    ovhcloud: 'bg-purple-100 text-purple-700',
    openai: 'bg-green-100 text-green-700',
    local: 'bg-gray-100 text-gray-700',
  }

  const color = colorMap[provider] || colorMap.local

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${color}`}>
      <span>🤖</span>
      <span>{provider}</span>
      {confidence > 0 && <span>({confidence.toFixed(0)}%)</span>}
    </div>
  )
}
```

---

## 📋 Checklist de Implementación

### Fase 1: Backend Endpoints (2 horas)

- [ ] Verificar `/imports/uploads/analyze` retorna AnalyzeResponse completo
- [ ] Implementar `/imports/ai/health` correctamente
- [ ] Validar `/imports/ai/telemetry` con costos
- [ ] Añadir logging de ai_provider en todas las respuestas
- [ ] Tests de endpoints con pytest

### Fase 2: Frontend Integración (3 horas)

- [ ] Actualizar Wizard.tsx para usar analyzeApi
- [ ] Crear AIProviderBadge.tsx
- [ ] Actualizar componentes para mostrar ai_provider
- [ ] Validar flujo completo upload → classify → map → confirm
- [ ] Tests con Playwright

### Fase 3: Error Handling (2 horas)

- [ ] Error boundaries en componentes críticos
- [ ] Fallback visual cuando IA no disponible
- [ ] Mensajes de error claros
- [ ] Retry automático

### Fase 4: Validación End-to-End (2 horas)

- [ ] Test manual con Ollama
- [ ] Test manual con OVHCloud
- [ ] Test fallback (Ollama falla → OVHCloud)
- [ ] Test performance
- [ ] Verificar logs completos

---

## 🚀 Orden de Ejecución

```
1. BACKEND
   ├── Verificar endpoints existentes
   ├── Implementar health check
   ├── Validar respuestas
   └── Escribir tests

2. FRONTEND
   ├── Crear AIProviderBadge
   ├── Actualizar Wizard
   ├── Integrar analyzeFile hook
   └── Validar flujo

3. TESTING
   ├── E2E Playwright
   ├── Manual con archivos reales
   ├── Verificar costos (OVHCloud)
   └── Performance

4. DEPLOYMENT
   ├── Desarrollo (Ollama)
   ├── Staging (OVHCloud)
   ├── Producción (OVHCloud)
   └── Monitoreo
```

---

## 📝 Archivos a Modificar/Crear

### Crear (Nuevos)
- [ ] `AIProviderBadge.tsx` (50 líneas)
- [ ] `components/AIProviderIndicator.tsx` (80 líneas)
- [ ] Tests para nuevos componentes (100 líneas)

### Actualizar (Existentes)
- [ ] `Wizard.tsx` - Integrar analyzeFile
- [ ] `useAnalyzeFile.ts` - Mejorar respuesta
- [ ] `importsApi.ts` - Añadir ai_provider tracking
- [ ] `.../interface/http/analyze.py` - Validar respuesta

### Backend Tests
- [ ] `tests/imports/test_ai_integration.py`
- [ ] `tests/imports/test_analyze_endpoint.py`

---

## 🔍 Validación Final

### Checklist Funcional

- [ ] Subir archivo Excel
  - [ ] Se detecta tipo automáticamente
  - [ ] Se muestra ai_provider usado
  - [ ] Se muestra confianza (%)
  - [ ] Se sugiere mapeo
- [ ] Subir archivo CSV
  - [ ] Idem anterior
- [ ] Subir archivo con baja confianza
  - [ ] IA mejora confianza
  - [ ] Se muestra badge de provider
- [ ] Offline (sin internet)
  - [ ] Fallback a local o Ollama
  - [ ] No crashea
- [ ] Con OVHCloud
  - [ ] Conecta correctamente
  - [ ] Retorna resultados
  - [ ] Telemetría registra costos

---

## ⏱️ Estimación de Tiempo

| Fase | Tarea | Tiempo |
|------|-------|--------|
| 1 | Backend verification | 1h |
| 2 | Frontend integration | 2h |
| 3 | Components & UI | 1h |
| 4 | Error handling | 1h |
| 5 | Testing | 2h |
| 6 | Documentation | 1h |
| **TOTAL** | | **8 horas** |

---

## 🎯 Resultado Final

**Después de implementar esto:**

✅ Sistema 100% funcional de importer + IA
✅ Frontend integrado completamente
✅ Backend validado
✅ Ollama en desarrollo, OVHCloud en producción
✅ Error handling robusto
✅ Testing completo
✅ Documentación actualizada

---

## 🚀 Comienza Con

1. **Lee este documento**
2. **Ejecuta implementación por fase**
3. **Valida cada cambio**
4. **Testing al final**
5. **Deploy cuando esté 100%**

---

**Próximo paso:** Empezar con implementación (abajo están los archivos específicos a crear/modificar)
