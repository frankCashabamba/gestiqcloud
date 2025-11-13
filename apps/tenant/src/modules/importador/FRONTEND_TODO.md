# 📋 Frontend Importador - TODO List

## Estado: 66% completado (Backend-first approach)

El frontend tiene la infraestructura base pero falta integración con Fase D (IA) y persistencia completa en Fase A.

---

## 🎯 Prioridad ALTA - Bloqueadores Críticos

### 1. Integrar Clasificación Automática en Upload (Fase A)
**Estado**: `ClassificationSuggestion.tsx` existe pero NO se usa en `Wizard.tsx`

**Archivos a modificar**:
- `Wizard.tsx` - Paso 1 (Upload)
  - [ ] Importar `classifyApi.ts`
  - [ ] Importar `ClassificationSuggestion.tsx`
  - [ ] Llamar `classifyFileWithAI()` después de upload
  - [ ] Mostrar resultado en paso 1 o 2
  - [ ] Permitir override manual de tipo de documento

**Pseudocódigo**:
```tsx
const [classifyResult, setClassifyResult] = useState<ClassifyResponse | null>(null)
const [classifyLoading, setClassifyLoading] = useState(false)

const handleUpload = async (file: File) => {
  setClassifyLoading(true)
  try {
    const result = await classifyFileWithAI(file)
    setClassifyResult(result)
    // Sugerir tipo de documento basado en resultado
    setDocType(result.suggested_parser)
  } finally {
    setClassifyLoading(false)
  }
}

return (
  <>
    <input type="file" onChange={(e) => handleUpload(e.target.files[0])} />
    {classifyResult && (
      <ClassificationSuggestion 
        result={classifyResult}
        loading={classifyLoading}
        error={null}
        confidence="high"
      />
    )}
  </>
)
```

**Estimado**: 2-3 horas

---

### 2. Persistir Clasificación Manual en ImportItem (Fase A)
**Estado**: Backend acepta pero frontend no envía

**Archivos a modificar**:
- `importsApi.ts` - Añadir campo a `CreateBatchPayload`
- `Wizard.tsx` - Enviar `suggested_parser` al crear batch

**Cambios**:
```typescript
export type CreateBatchPayload = {
  source_type: string
  origin: string
  suggested_parser?: string  // ⭐ AÑADIR
  classification_confidence?: number  // ⭐ AÑADIR
  ai_enhanced?: boolean  // ⭐ AÑADIR
  ai_provider?: string  // ⭐ AÑADIR
  // ... resto de campos
}
```

**Estimado**: 1-2 horas

---

## 🎯 Prioridad ALTA - Fase D (IA Configurable)

### 3. Badge Visual de Proveedor IA (Fase D)
**Estado**: Backend envía `enhanced_by_ai` + `ai_provider`, frontend NO lo muestra

**Archivos a crear/modificar**:
- Crear `components/AIProviderBadge.tsx`
- Modificar `Wizard.tsx` - Mostrar badge en header o paso 6
- Modificar `ResumenImportacion.tsx` - Mostrar badge en resumen

**Requerimiento**:
```tsx
interface AIProviderBadge {
  provider: 'local' | 'openai' | 'azure'
  enhanced: boolean
  confidence?: number
}

// Mostrar: "🤖 IA: Local" o "🤖 IA: OpenAI (Gpt-3.5)"
```

**Estimado**: 1-2 horas

---

### 4. Settings Frontend - Selector de Proveedor IA
**Estado**: No existe en frontend

**Archivos a crear**:
- Crear `modules/settings/ImportadorSettings.tsx`
- Crear `services/aiProviderSettings.ts` (localStorage temporalmente)
- Integrar en settings existentes

**Requerimiento**:
```typescript
interface AIProviderSetting {
  provider: 'local' | 'openai' | 'azure'
  openaiApiKey?: string
  azureEndpoint?: string
  azureKey?: string
  confidenceThreshold: number  // 0-1
  enableCache: boolean
  enableTelemetry: boolean
}
```

**UI esperada**:
```
┌─────────────────────────────────────────┐
│ ⚙️ Configuración de IA                   │
├─────────────────────────────────────────┤
│ Proveedor: [Local ▼]                    │
│ Umbral de confianza: [0.7]              │
│ ☑ Caché habilitado (24h)                │
│ ☑ Telemetría habilitada                 │
│                                          │
│ ℹ️ Proveedor actual: Local (gratuito)   │
│    OpenAI (pago) | Azure (pago)         │
└─────────────────────────────────────────┘
```

**Estimado**: 3-4 horas

---

### 5. Dashboard de Telemetría IA (Fase D)
**Estado**: Backend guarda, frontend NO muestra

**Archivos a crear**:
- Crear `modules/importador/components/AITelemetryDashboard.tsx`
- Crear `services/telemetryApi.ts`

**Métricas a mostrar**:
- Accuracy promedio de clasificaciones
- Latencia promedio (ms)
- Total de clasificaciones
- Desglose por proveedor
- Tendencia últimos 30 días

**Estimado**: 4-5 horas

---

## 🎯 Prioridad MEDIA

### 6. Tests de Componentes IA (Fase D)
**Estado**: No hay tests

**Archivos a crear**:
- `__tests__/components/ClassificationSuggestion.test.tsx`
- `__tests__/services/classifyApi.test.ts`
- `__tests__/Wizard.integration.test.tsx`

**Estimado**: 3-4 horas

---

### 7. Documentación Frontend - IA Integration (Fase E)
**Estado**: Existe MEJORAS_IMPLEMENTADAS.md pero no documenta IA

**Archivos a crear/modificar**:
- Crear `docs/IA_INTEGRATION.md` en frontend
- Actualizar `README.md` con sección IA
- Crear `docs/CLASSIFYAPI_USAGE.md`

**Contenido esperado**:
- Flujo de clasificación
- Ejemplos de uso
- Configuración de proveedores
- Troubleshooting
- Performance tips

**Estimado**: 2-3 horas

---

### 8. Soporte para Parser Registry en Frontend (Fase B)
**Estado**: Parcial - se detectan tipos pero no se expone registry

**Archivos a crear**:
- Crear `services/parserRegistry.ts`
- Endpoint GET `/api/v1/imports/parsers/registry` (backend)

**Requerimiento**:
```typescript
interface ParserMetadata {
  id: string
  name: string
  doc_type: 'products' | 'expenses' | 'invoice' | 'bank' | ...
  supported_extensions: string[]
  max_file_size: number
  description: string
}

// Frontend expone selector dinámico basado en registry
```

**Estimado**: 2-3 horas

---

## 🎯 Prioridad BAJA - UX Enhancements

### 9. Mostrar Errores por Validador de País (Fase C)
**Estado**: Se muestran errores pero genéricos

**Mejora**:
- Agrupar errores por país/validador
- Mostrar sugerencias de corrección
- Link a documentación del validador

**Estimado**: 2-3 horas

---

### 10. Indicador de Progreso WebSocket (Fase E)
**Estado**: Hook existe pero no integrado

**Archivos a modificar**:
- `hooks/useImportProgress.tsx` - Ya existe
- `Wizard.tsx` Paso 6 - Conectar WebSocket

**Cambio**:
```tsx
const { progress, error, connected } = useImportProgress(batchId)

return (
  <ProgressIndicator 
    current={progress.current}
    total={progress.total}
    estimatedSecondsRemaining={progress.estimated_time_remaining}
    status={progress.status}
    connected={connected}
  />
)
```

**Estimado**: 1-2 horas

---

## 📊 Resumen de Desarrollo

| Tarea | Prioridad | Estimado | Archivos | Estado |
|-------|-----------|----------|----------|--------|
| 1. Integrar clasificación en Upload | 🔴 ALTA | 2-3h | 1 | ⏳ TODO |
| 2. Persistir clasificación manual | 🔴 ALTA | 1-2h | 2 | ⏳ TODO |
| 3. Badge visual IA | 🔴 ALTA | 1-2h | 3 | ⏳ TODO |
| 4. Settings IA | 🔴 ALTA | 3-4h | 3 | ⏳ TODO |
| 5. Dashboard telemetría | 🟠 MEDIA | 4-5h | 2 | ⏳ TODO |
| 6. Tests componentes | 🟠 MEDIA | 3-4h | 3 | ⏳ TODO |
| 7. Documentación IA | 🟠 MEDIA | 2-3h | 2 | ⏳ TODO |
| 8. Parser registry dinámico | 🟠 MEDIA | 2-3h | 1 | ⏳ TODO |
| 9. Errores por país | 🟡 BAJA | 2-3h | 1 | ⏳ TODO |
| 10. WebSocket progreso | 🟡 BAJA | 1-2h | 1 | ✅ PARCIAL |

**Total estimado**: 21-29 horas (3-4 días de desarrollo)

---

## 🚀 Recomendación de Orden

### Sprint 1 (Crítico - 8 horas):
1. ✅ Integrar clasificación en Upload (2-3h)
2. ✅ Persistir clasificación (1-2h)
3. ✅ Badge visual IA (1-2h)
4. ✅ WebSocket progreso (1-2h)

### Sprint 2 (Importante - 8 horas):
5. ✅ Settings IA (3-4h)
6. ✅ Parser registry dinámico (2-3h)
7. ✅ Documentación IA (2-3h)

### Sprint 3 (Enhancements - 8 horas):
8. ✅ Dashboard telemetría (4-5h)
9. ✅ Tests (3-4h)
10. ✅ Errores por país (2-3h)

---

## 🔗 Dependencias

- ✅ Backend Fase D completada (`/classify`, `/classify-with-ai`)
- ✅ Backend endpoints telemetría (`/imports/ai/telemetry`)
- ✅ Backend WebSocket progreso (`/ws/imports/progress/{batchId}`)
- ⏳ Backend tabla `ImportTemplate` (para plantillas)
- ⏳ Backend endpoints plantillas (`/api/v1/imports/templates`)

---

## 💡 Notas

1. El frontend ya tiene el 70% de la plumería lista
2. Falta principalmente conectar lo existente entre componentes
3. Fase D necesita UI/UX pulida (badges, settings, dashboard)
4. Backend está 100% listo; este es un documento puro frontend
5. Recomendable hacer primero tasks críticas de Fase A antes de Fase D

---

**Última actualización**: 11 Nov 2025  
**Autor**: AI Code Review  
**Estado**: En planificación
