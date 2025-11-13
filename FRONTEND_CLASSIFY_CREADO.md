# Frontend Classify - Implementación Completada

**Fecha:** 11/11/2025  
**Estado:** ✅ Completado

## Archivos Creados

### 1. Servicio API
**Ubicación:** `apps/tenant/src/modules/importador/services/classifyApi.ts`

**Funciones:**
- `classifyFileBasic(file: File)` - Clasificación con análisis heurístico
- `classifyFileWithAI(file: File)` - Clasificación con IA
- `classifyFile(file: File, useAI?: boolean)` - Wrapper con fallback automático

**Tipos:**
```typescript
interface ClassifyResponse {
  suggested_parser: string
  confidence: number
  reason: string
  available_parsers: string[]
  content_analysis?: { headers?: string[], scores?: Record<string, number> }
  probabilities?: Record<string, number>
  enhanced_by_ai?: boolean
  ai_provider?: string
}
```

---

### 2. Hook React
**Ubicación:** `apps/tenant/src/modules/importador/hooks/useClassifyFile.ts`

**Interfaz:**
```typescript
interface UseClassifyFileState {
  loading: boolean
  error: Error | null
  result: ClassifyResponse | null
  confidence: 'high' | 'medium' | 'low' | null
}
```

**Métodos:**
- `classify(file: File, useAI?: boolean)` - Ejecuta clasificación
- `reset()` - Limpia estado

**Ejemplo de uso:**
```typescript
const { classify, loading, result, error, confidence } = useClassifyFile()

await classify(file)
// => result = { suggested_parser: 'products_excel', confidence: 0.92, ... }
// => confidence = 'high' (≥80%)
```

---

### 3. Componente UI
**Ubicación:** `apps/tenant/src/modules/importador/components/ClassificationSuggestion.tsx`

**Props:**
```typescript
interface ClassificationSuggestionProps {
  result: ClassifyResponse | null
  loading: boolean
  error: Error | null
  confidence: 'high' | 'medium' | 'low' | null
}
```

**Features:**
- Badge circular de confianza (coloreado: verde/amarillo/rojo)
- Spinner de carga
- Manejo de errores con ícono y mensaje
- Razón de clasificación
- Badge "Potenciado con IA" cuando aplica
- Gráfico de probabilidades (top 6 parsers)
- Lista de parsers disponibles
- Estilos CSS inline (TailwindCSS compatible)

---

### 4. Integración en Wizard
**Ubicación:** `apps/tenant/src/modules/importador/Wizard.tsx`

**Cambios realizados:**
- Importa `useClassifyFile` hook
- Extrae `confidence` del hook
- Pasa `confidence` prop a `ClassificationSuggestion`
- Se renderiza en paso 'preview' (después de upload)

**Flujo:**
```
Upload → Parse CSV → Classify (IA) → Preview (Muestra ClassificationSuggestion) → Mapping
```

---

## Flujo de Uso

### 1. Usuario sube archivo
```typescript
const file = e.target.files[0]
```

### 2. Wizard clasifica automáticamente
```typescript
await classify(file) // Hook useClassifyFile
```

### 3. Se muestra sugerencia en preview
```tsx
<ClassificationSuggestion
  result={classificationResult}
  loading={classifying}
  error={classificationError}
  confidence={confidence}
/>
```

### 4. Usuario ve:
- ✅ Parser sugerido (ej: "products_excel")
- ✅ Confianza: 92% (badge verde)
- ✅ Razón: "Detected product-related columns"
- ✅ Badge: "🤖 Potenciado con openai"
- ✅ Top 6 probabilidades con barras
- ✅ Lista de parsers disponibles

---

## Características Implementadas

| Característica | Estado |
|---|---|
| Llamada a API `/imports/files/classify` | ✅ |
| Llamada a API `/imports/files/classify-with-ai` | ✅ |
| Fallback automático (IA → básico) | ✅ |
| Hook con estado (loading/error/result) | ✅ |
| Cálculo de confianza (high/medium/low) | ✅ |
| Componente UI con badge coloreado | ✅ |
| Spinner durante clasificación | ✅ |
| Manejo de errores con UI | ✅ |
| Mostrador de probabilidades | ✅ |
| Badge "Potenciado con IA" | ✅ |
| Integración en Wizard | ✅ |
| Estilos CSS responsive | ✅ |

---

## Pendiente (Próximas tareas)

- [ ] Tests unitarios del hook
- [ ] Tests del componente
- [ ] Tests de integración en Wizard
- [ ] Documentación en Swagger
- [ ] Tests backend (endpoints)

---

## Contacto
Creado por: Sistema Amp  
Fecha: 11/11/2025
