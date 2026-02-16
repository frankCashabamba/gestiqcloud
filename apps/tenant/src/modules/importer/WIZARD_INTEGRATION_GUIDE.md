# 📋 Guía de Integración - Actualizar Wizard.tsx

**Objetivo:** Integrar completamente los nuevos componentes IA en el Wizard

---

## 🎯 Cambios Necesarios en Wizard.tsx

### 1. Importar nuevos componentes

```typescript
// Agregar después de las importaciones existentes
import { AnalysisResultDisplay } from './components/AnalysisResultDisplay'
import { AIProviderBadge, AIProviderStatus } from './components/AIProviderBadge'
import { AIHealthIndicator } from './components/AIHealthIndicator'
```

### 2. Actualizar el Hook useAnalyzeFile

**Antes (actual):**
```typescript
const {
  analyze,
  loading: analyzing,
  result: analysisResult,
  error: analysisError,
  requiresConfirmation,
  reset: resetAnalysis,
} = useAnalyzeFile()
```

**Después (mejorado):**
```typescript
const {
  analyze,
  loading: analyzing,
  result: analysisResult,
  error: analysisError,
  requiresConfirmation,
  confidence,  // NUEVO: nivel de confianza
  reset: resetAnalysis,
} = useAnalyzeFile()
```

### 3. Paso de Upload - Integrar Análisis

**Ubicación:** Donde se procesa el archivo después de upload

**Antes:**
```typescript
// clasificar archivo
const classification = await classify(file)
```

**Después:**
```typescript
// Analizar archivo (incluye clasificación + mapeo)
const analysis = await analyze(file)

if (analysis) {
  // Guardar información de IA
  setAiProviderUsed(analysis.ai_provider)
  setAiConfidence(analysis.confidence)
  setAiEnhanced(analysis.ai_enhanced)
  
  // Si hay mapeo sugerido, pre-poblar
  if (analysis.mapping_suggestion) {
    setMapa(analysis.mapping_suggestion)
  }
}
```

### 4. Paso de Mapping - Mostrar Componentes Nuevos

**Ubicación:** Sección de mapping en el Wizard

**Agregar al inicio:**
```tsx
{/* Mostrar resultado del análisis IA */}
{analysisResult && (
  <AnalysisResultDisplay
    analysis={analysisResult}
    onConfirm={() => {
      // Confirmar y pasar al siguiente paso
      setStep('validate')
    }}
    onEdit={() => {
      // Permitir edición del mapeo
      // Ya está en la UI de MapeoCampos
    }}
    loading={analyzing}
  />
)}

{/* Indicador de health de IA */}
<div className="mt-4 flex items-center justify-between">
  <span className="text-sm text-gray-600">Estado del sistema IA:</span>
  <AIHealthIndicator />
</div>
```

### 5. Paso de Validate - Guardar Información de IA

**Ubicación:** Al crear el batch

**Antes:**
```typescript
const batch = await createBatch({
  entityType: docType,
  sourceType: 'xlsx',
  parserChoice: classificationResult?.suggested_parser,
})
```

**Después:**
```typescript
const batch = await createBatch({
  entityType: docType,
  sourceType: 'xlsx',
  parserChoice: analysisResult?.suggested_parser,
  // NUEVO: metadata de IA
  aiProvider: analysisResult?.ai_provider,
  aiConfidence: analysisResult?.confidence,
  aiEnhanced: analysisResult?.ai_enhanced,
  decisionLog: analysisResult?.decision_log,
})
```

### 6. Paso de Summary - Mostrar Badge de Proveedor

**Ubicación:** En la sección de resumen

**Agregar:**
```tsx
<div className="flex items-center gap-2">
  <span className="text-sm font-medium">Documento clasificado con:</span>
  <AIProviderBadge
    provider={analysisResult?.ai_provider}
    confidence={analysisResult?.confidence}
    enhanced={analysisResult?.ai_enhanced}
    size="md"
  />
</div>

{/* Mostrar advertencia si confianza baja */}
{analysisResult && analysisResult.confidence < 0.7 && (
  <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-900">
    ⚠️ Confianza moderada ({(analysisResult.confidence * 100).toFixed(0)}%).
    Revisa cuidadosamente el mapeo antes de importar.
  </div>
)}
```

---

## 📝 Propiedades de Estado a Agregar

```typescript
// Agregar al estado del Wizard
const [aiProviderUsed, setAiProviderUsed] = useState<string | null>(null)
const [aiConfidence, setAiConfidence] = useState<number>(0)
const [aiEnhanced, setAiEnhanced] = useState(false)
```

---

## 🔄 Flujo Completo Actualizado

```
1. Usuario sube archivo
   ↓
2. analyzeFile() retorna AnalyzeResponse
   - suggested_parser
   - suggested_doc_type
   - confidence
   - mapping_suggestion
   - ai_provider ("ollama" / "ovhcloud" / etc)
   - ai_enhanced (boolean)
   ↓
3. Mostrar AnalysisResultDisplay
   - Display de análisis
   - AIProviderBadge con provider usado
   - Confianza visual
   - Mapeo sugerido
   ↓
4. Usuario confirma o edita
   ↓
5. Guardar análisis en batch metadata
   - ai_provider
   - ai_confidence
   - ai_enhanced
   - decision_log
   ↓
6. Mostrar en Summary con AIProviderBadge
   ↓
7. Importar
```

---

## ⚙️ Actualización de Types

**Verificar que AnalyzeResponse incluye:**
```typescript
interface AnalyzeResponse {
  suggested_parser: string
  suggested_doc_type: string
  confidence: number
  headers_sample: string[]
  mapping_suggestion: Record<string, string> | null
  explanation: string
  decision_log: Array<{
    step: string
    timestamp?: string
    input_data?: Record<string, unknown>
    output_data?: Record<string, unknown>
    confidence?: number
    duration_ms?: number
  }>
  requires_confirmation: boolean
  available_parsers: string[]
  probabilities: Record<string, number> | null
  ai_enhanced: boolean
  ai_provider: string | null
}
```

---

## 🧪 Testing Checklist

Después de integrar, verifica:

- [ ] Subir archivo Excel → Se analiza correctamente
- [ ] Se muestra AnalysisResultDisplay con provider
- [ ] Se muestra AIProviderBadge
- [ ] Se pre-populan headers y mapping
- [ ] Confianza se muestra visualmente
- [ ] Al confirmar, se guardan datos de IA
- [ ] En summary se muestra provider usado
- [ ] Importación completa exitosamente
- [ ] Health indicator se actualiza

---

## 🐛 Troubleshooting

**Si analyzeFile retorna null:**
- Verificar que `/imports/uploads/analyze` endpoint responde
- Revisar logs del backend
- Comprobar que archivo se subió correctamente

**Si AIProviderBadge no se muestra:**
- Verificar que `ai_enhanced = true`
- Verificar que `ai_provider != null`
- Comprobar CSS classes de tailwind

**Si confianza no se actualiza:**
- Verificar que `analysisResult.confidence` tiene valor
- Comprobar que componente re-renderiza

---

## 📚 Referencia de Componentes

### AnalysisResultDisplay
- Props: `analysis`, `onConfirm`, `onEdit`, `loading`
- Muestra resultado completo del análisis
- Incluye decisión log, probabilidades, etc

### AIProviderBadge
- Props: `provider`, `confidence`, `enhanced`, `size`
- Badge visual del provider IA usado
- Colores por provider

### AIHealthIndicator
- Props: `className`, `showDetails`
- Muestra estado del sistema IA
- Auto-refetch cada 30s

---

## 🚀 Orden de Implementación

1. Agregar importaciones en Wizard.tsx
2. Agregar estado para IA metadata
3. Actualizar paso de upload
4. Actualizar paso de mapping
5. Actualizar paso de validate
6. Actualizar paso de summary
7. Testing

---

**Siguiente paso:** Implementar cambios en orden y probar cada paso
