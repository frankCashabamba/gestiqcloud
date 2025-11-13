# Frontend Sprint 1 - Clasificación + Metadatos

## Objetivo
Integrar el componente `ClassificationSuggestion` en el Wizard paso 1/2, conectar con API de clasificación, y persistir resultados en los batches.

## Tareas Críticas (Sprint 1)

### 1. ✅ Crear servicio `classifyApi.ts`
**Archivo**: `services/classifyApi.ts`

**Descripción**: Consumidor de endpoints del backend para clasificación de archivos.

**Endpoints**:
- `POST /imports/files/classify` - Clasificación básica (heurística local)
- `POST /imports/files/classify-with-ai` - Clasificación con IA (local/OpenAI/Azure)

**Interfaz esperada**:
```typescript
export interface ClassifyResponse {
  suggested_parser: string
  confidence: number
  reason?: string
  enhanced_by_ai: boolean
  ai_provider?: string
  probabilities?: Record<string, number>
  available_parsers?: string[]
}
```

**Métodos**:
- `classifyFileBasic(file: File): Promise<ClassifyResponse>`
- `classifyFileWithAI(file: File): Promise<ClassifyResponse>`
- Ambos con fallback a heurística si falla

---

### 2. ✅ Crear hook `useClassifyFile.ts`
**Archivo**: `hooks/useClassifyFile.ts`

**Descripción**: Hook que encapsula la lógica de clasificación de archivos.

**Estados manejados**:
- `loading` - Está clasificando
- `result` - Resultado de la clasificación
- `error` - Errores en la clasificación
- `confidence` - Nivel de confianza (high/medium/low)

**Métodos**:
- `classify(file: File): Promise<void>` - Ejecutar clasificación

---

### 3. ✅ Integrar `ClassificationSuggestion` en `Wizard.tsx`
**Ubicación**: Paso 2 (Preview) - Ya existe la integración en línea 209-215

**Status actual**:
- El componente está importado ✅
- Se pasa `result`, `loading`, `error`, `confidence` ✅
- Hook `useClassifyFile` se usa correctamente ✅

**Pendiente**:
- Verificar que `classify(f)` se ejecute con el archivo correcto
- Manejar errores gracefully (fallback a heurística)

---

### 4. ⚠️ Persistir clasificación en ImportBatch
**Endpoints del backend ya listos**:
- ✅ `POST /imports/batches` - Acepta `suggested_parser`, `ai_enhanced`, `ai_provider`, `classification_confidence`
- ✅ `PATCH /imports/batches/{id}/classification` - Actualiza clasificación
- ✅ `POST /imports/batches/{id}/classify-and-persist` - Todo en uno

**A hacer en frontend**:
- [ ] Enviar campos de clasificación al crear batch
- [ ] Mostrar badge IA en la UI

---

### 5. 🤖 Badge visual "IA: Local/OpenAI/Azure"
**Ubicación**: `ClassificationSuggestion.tsx` línea 99-103 ya existe

**Estado actual**:
```typescript
{result.enhanced_by_ai && (
  <div className="classification-suggestion__ai-enhanced">
    <span className="ai-badge">🤖 Potenciado con {result.ai_provider || 'IA'}</span>
  </div>
)}
```

**Status**: ✅ IMPLEMENTADO

---

### 6. 🔄 Integración de clasificación en el flow
**Current flow en `Wizard.tsx`** (líneas 82-87):
```typescript
// Clasificar archivo con IA
try {
    await classify(f)
} catch (err) {
    console.warn('IA classification failed, using heuristic:', err)
}
```

**Pendiente**:
- Guardar resultado en estado persistente
- Usar en el batch creation

---

## Arquitectura

```
Wizard.tsx
├── onFile() - Upload
├── classify(file) ← useClassifyFile hook
│   └── classifyApi.classifyFileWithAI()
│       └── POST /imports/files/classify-with-ai
└── createBatch() - Al final, pasar campos:
    └── {
      source_type, origin,
      suggested_parser,      ← DEL CLASSIFICATION RESULT
      classification_confidence,
      ai_enhanced, ai_provider
    }
```

---

## Estado Actual de Componentes

| Componente | Estado | Ubicación |
|-----------|--------|-----------|
| `Wizard.tsx` | ✅ Importa ClassificationSuggestion | `Wizard.tsx:12` |
| `ClassificationSuggestion.tsx` | ✅ Componente completo | `components/ClassificationSuggestion.tsx` |
| `classifyApi.ts` | ❌ NO EXISTE | `services/classifyApi.ts` |
| `useClassifyFile.ts` | ❌ NO EXISTE | `hooks/useClassifyFile.ts` |
| Backend endpoints | ✅ LISTOS | Backend (Fase A 71%) |

---

## Checklist

- [x] Crear `services/classifyApi.ts` con endpoints ✅
- [x] Crear `hooks/useClassifyFile.ts` con lógica ✅
- [x] Verificar Wizard.tsx usa hook correctamente ✅
- [x] Actualizar tipos en `importsApi.ts` para campos clasificación ✅
- [x] Modificar `Wizard.tsx` onImportAll() para pasar campos clasificación ✅
- [ ] Testar flujo completo (upload → classify → preview → create batch)
- [ ] Testar fallback si IA falla
- [ ] Verificar que backend recibe los campos correctamente
- [ ] Documentar ejemplos de uso

---

## Estimado
**Horas**: 2-3 horas
**Complejidad**: Baja-Media

## Siguiente
Sprint 2: Integrar persistencia en pasos 4-5 del wizard
