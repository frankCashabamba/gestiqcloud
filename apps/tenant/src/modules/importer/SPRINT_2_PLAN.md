# Frontend Sprint 2 - Override Manual + Badges Visuales

**Basado en**: Sprint 1 completado (Nov 11, 2025)

## Objetivo
Mejorar UX permitiendo override manual del parser clasificado y mostrando indicadores visuales de IA en toda la UI.

## Tareas Críticas (Sprint 2)

### 1. Override Manual del Parser (Paso 4-5)
**Ubicación**: `Wizard.tsx` paso mapping/validate/summary

**Requerimiento**:
- Mostrar parser sugerido actual (del resultado de IA)
- Permitir usuario cambiar a otro parser disponible
- Guardar selección manual en estado

**Implementación**:
```typescript
// En Wizard.tsx
const [selectedParser, setSelectedParser] = useState<string | null>(null)

// En paso mapping o validate:
<div className="parser-selector">
  <label>Parser seleccionado:</label>
  <select value={selectedParser || classificationResult?.suggested_parser || ''}>
    <option value="">-- Usar sugerencia --</option>
    {classificationResult?.available_parsers?.map(p => (
      <option key={p} value={p}>{p}</option>
    ))}
  </select>
  {selectedParser && (
    <span className="badge badge-warning">Override manual</span>
  )}
</div>
```

**Al crear batch, usar selección manual si existe:**
```typescript
const finalParser = selectedParser || classificationResult?.suggested_parser
```

---

### 2. Badge de Clasificación en Batch Card
**Ubicación**: Paso 5 (Summary) - `ResumenImportacion.tsx`

**Muestra**:
- Parser: `xlsx_products` o similar
- Confianza: `92%` (color verde si >80%, amarillo si 60-80%, rojo si <60%)
- Proveedor: `Local` o `OpenAI` o `Azure`

**Implementación**:
```typescript
// En ResumenImportacion.tsx
{classificationResult && (
  <div className="classification-card">
    <div className="parser-badge">{classificationResult.suggested_parser}</div>
    <div className="confidence-badge" style={{
      background: confidence > 0.8 ? '#10b981' : confidence > 0.6 ? '#f59e0b' : '#ef4444'
    }}>
      {Math.round(classificationResult.confidence * 100)}%
    </div>
    <div className="provider-badge">
      {classificationResult.enhanced_by_ai ? `🤖 ${classificationResult.ai_provider}` : 'Heurística'}
    </div>
  </div>
)}
```

---

### 3. Actualizar ImportItem para Override
**Archivo**: `importsApi.ts`

**Extender tipo `ImportItem`** (opcional para futuro):
```typescript
export type ImportItem = {
  // ... campos existentes ...
  suggested_parser?: string | null
  parser_override?: string | null  // Si usuario cambió manualmente
}
```

---

### 4. UI Mejorada del Preview
**Ubicación**: Paso 2 (Preview) - `Wizard.tsx`

**Cambios**:
- Ampliar ClassificationSuggestion con opciones de selector
- Mostrar parsers disponibles en dropdown
- Indicar cuál es la selección actual

```typescript
// En preview, después de ClassificationSuggestion:
{classificationResult?.available_parsers && (
  <div className="parser-options">
    <label>Cambiar a otro parser:</label>
    <div className="parser-grid">
      {classificationResult.available_parsers.map(parser => (
        <button
          key={parser}
          className={selectedParser === parser ? 'active' : ''}
          onClick={() => setSelectedParser(parser)}
        >
          {parser}
        </button>
      ))}
    </div>
  </div>
)}
```

---

### 5. Mostrar Indicadores en BatchList
**Ubicación**: `ImportadosList.tsx` o batch card component

**Agregue**: Pequeño badge IA en card de batch
```typescript
{batch.ai_enhanced && (
  <span className="ai-indicator">
    🤖 {batch.ai_provider || 'IA'}
  </span>
)}
```

---

## Arquitectura

```
Wizard.tsx
├── [Estado] classificationResult (del hook)
├── [Estado] selectedParser (nuevo - override manual)
├── Paso 2: Preview
│   ├── ClassificationSuggestion (actual)
│   └── [NUEVO] Parser selector dropdown
├── Paso 4: Mapping
│   └── [NUEVO] Parser override option
└── Paso 5: Summary
    ├── [NUEVO] ClassificationCard con badges
    └── Resumen normal
```

---

## Archivos a Modificar

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| `Wizard.tsx` | Agregar estado selectedParser, mostrar selector | 45-300 |
| `ResumenImportacion.tsx` | Mostrar card con clasificación | 1-100 |
| `components/ClassificationCard.tsx` | [NUEVO] Componente para resumen | - |
| `importsApi.ts` | Extender ImportItem (opcional) | 14-22 |

---

## Criterios de Aceptación

- [x] Usuario puede ver parser sugerido en paso preview
- [x] Usuario puede cambiar a otro parser (paso mapping)
- [x] Selección manual se muestra con badge "Override"
- [x] En batch creation, usa selección manual si existe
- [x] Badge IA en summary muestra: parser + confianza + proveedor
- [x] Badge IA también aparece en batch card (ImportadosList)
- [x] Colores de confianza basados en score

---

## Testing

```typescript
// Test: User overrides parser
1. Upload CSV
2. Ver ClassificationSuggestion con parser = "xlsx_products"
3. Hacer click en parser diferente (ej. "csv_products")
4. Ver badge "Override manual"
5. Avanzar a batch creation
6. Verificar batch.suggested_parser = "csv_products" (el override)

// Test: Badge en summary
1. Completar flujo anterior
2. En paso summary, verificar ClassificationCard visible
3. Verificar muestra: "csv_products", "87%", "🤖 Local"
```

---

## Estimado
**Horas**: 4-5 horas
**Complejidad**: Media

## Siguiente
Sprint 3: Telemetría + Tests + WebSocket progreso
