# Sistema de Importación Inteligente - Testing

## ✅ Completado Backend

### 1. Migración Base de Datos
- ✅ Tabla `import_column_mappings` creada
- ✅ RLS policies aplicadas
- ✅ Índices creados

### 2. Modelo SQLAlchemy
- ✅ `ImportColumnMapping` en `app/models/imports.py`
- ✅ Registrado en `__init__.py`

### 3. Servicio Analizador
- ✅ `excel_analyzer.py` con:
  - `detect_header_row()` - Detecta automáticamente fila de encabezados
  - `suggest_column_mapping()` - Sugerencias por keywords
  - `analyze_excel_stream()` - Análisis completo

### 4. Endpoints API

#### POST `/api/v1/imports/analyze-file`
Analiza Excel y detecta columnas.
```bash
curl -X POST "http://localhost:8000/api/v1/imports/analyze-file" \
  -H "Authorization: Bearer <token>" \
  -F "file=@stock-28-10-20251.xlsx"
```

**Respuesta:**
```json
{
  "headers": ["FORMATO DE COMO APUNTAR LAS COMPRAS", ...],
  "header_row": 1,
  "sample_data": [{...}, {...}],
  "suggested_mapping": {
    "columna1": "name",
    "columna2": "precio"
  },
  "total_rows": 150,
  "total_columns": 7,
  "saved_mappings": []
}
```

#### POST `/api/v1/imports/column-mappings`
Guarda configuración de mapeo.
```bash
curl -X POST "http://localhost:8000/api/v1/imports/column-mappings" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Excel Proveedor XYZ",
    "description": "Formato mensual",
    "mapping": {
      "FORMATO DE COMO APUNTAR LAS COMPRAS": "name",
      "Precio $": "precio",
      "Stock": "cantidad"
    },
    "file_pattern": "stock-*.xlsx"
  }'
```

#### GET `/api/v1/imports/column-mappings`
Lista mapeos guardados del tenant.

#### DELETE `/api/v1/imports/column-mappings/{id}`
Elimina (soft delete) un mapeo.

#### POST `/api/v1/imports/batches/{batch_id}/ingest?column_mapping_id={uuid}`
Ingesta con mapeo aplicado automáticamente.

---

## 🧪 Flujo de Testing Manual

### Paso 1: Analizar el Excel
```bash
# 1. Subir Excel para análisis
curl -X POST "http://localhost:8000/api/v1/imports/analyze-file" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@stock-28-10-20251.xlsx" \
  | jq '.suggested_mapping'
```

**Resultado esperado:**
```json
{
  "FORMATO DE COMO APUNTAR LAS COMPRAS": "name"
}
```

### Paso 2: Crear Mapeo Manual
```bash
# 2. Usuario ajusta el mapeo y lo guarda
curl -X POST "http://localhost:8000/api/v1/imports/column-mappings" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Proveedor Paraiso",
    "mapping": {
      "FORMATO DE COMO APUNTAR LAS COMPRAS": "name",
      "Columna_2": "precio",
      "Columna_3": "cantidad"
    }
  }' | jq '.id'
```

**Guardar ID del mapeo:**
```
MAPPING_ID="89d56c87-5d65-4e42-9dc4-681c5cb47dce"
```

### Paso 3: Crear Batch
```bash
# 3. Crear batch de importación
curl -X POST "http://localhost:8000/api/v1/imports/batches" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "productos",
    "name": "Import Octubre 2025"
  }' | jq '.id'
```

**Guardar ID del batch:**
```
BATCH_ID="f1234567-89ab-cdef-0123-456789abcdef"
```

### Paso 4: Ingestar con Mapeo
```bash
# 4. Leer Excel y enviar filas con column_mapping_id
python << 'EOF'
import openpyxl
import requests
import os

wb = openpyxl.load_workbook('stock-28-10-20251.xlsx')
ws = wb.active

rows = []
for row_idx in range(2, min(100, ws.max_row + 1)):
    row_data = {}
    for col_idx, cell in enumerate(ws[row_idx]):
        header = ws.cell(1, col_idx + 1).value
        if header:
            row_data[header] = cell.value
    if any(row_data.values()):
        rows.append(row_data)

# Enviar con column_mapping_id
response = requests.post(
    f"http://localhost:8000/api/v1/imports/batches/${BATCH_ID}/ingest",
    headers={"Authorization": f"Bearer {os.getenv('TOKEN')}"},
    params={"column_mapping_id": "${MAPPING_ID}"},
    json={"rows": rows}
)
print(response.json())
EOF
```

### Paso 5: Verificar Items
```bash
# 5. Verificar que items tienen nombre mapeado correctamente
curl "http://localhost:8000/api/v1/imports/batches/${BATCH_ID}/items?limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  | jq '.[] | {idx, status, name: .normalized.name, precio: .normalized.precio}'
```

**Esperado:**
```json
{
  "idx": 1,
  "status": "OK",
  "name": "chochos",  ← Nombre mapeado correctamente
  "precio": 1.50
}
```

### Paso 6: Promover a Productos
```bash
# 6. Promover items a productos
curl -X POST "http://localhost:8000/api/v1/imports/items/promote" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "item_ids": ["item-uuid-1", "item-uuid-2"]
  }'
```

---

## 📊 Validación en Base de Datos

```sql
-- Ver mapeos guardados
SELECT id, name, mapping, use_count, last_used_at
FROM import_column_mappings
WHERE tenant_id = '5c7bea07-05ca-457f-b321-722b1628b170';

-- Ver estadísticas de uso
SELECT
    name,
    use_count,
    last_used_at,
    json_object_keys(mapping) as mapped_columns
FROM import_column_mappings;
```

---

## 🎨 Frontend UI (Próximo)

### Componente ColumnMappingStep.tsx

```typescript
interface ColumnMappingStepProps {
  detectedColumns: string[];
  sampleData: Record<string, any>[];
  suggestedMapping: Record<string, string>;
  savedMappings: SavedMapping[];
  onConfirm: (mapping: Record<string, string>, saveName?: string) => void;
}

function ColumnMappingStep({ ... }: ColumnMappingStepProps) {
  const [mapping, setMapping] = useState(suggestedMapping);
  const [saveName, setSaveName] = useState('');

  const targetFields = [
    { value: 'name', label: '📦 Nombre Producto *', required: true },
    { value: 'precio', label: '💰 Precio Venta' },
    { value: 'cantidad', label: '📊 Stock' },
    { value: 'categoria', label: '🏷️ Categoría' },
    { value: 'codigo', label: '🔢 Código/SKU' },
    { value: 'costo', label: '💸 Costo Compra' },
    { value: 'ignore', label: '❌ Ignorar' }
  ];

  return (
    <div className="p-6">
      <h3 className="text-lg font-bold mb-4">
        Mapeo de Columnas
      </h3>

      {/* Selector de mapeo guardado */}
      {savedMappings.length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Cargar mapeo guardado:
          </label>
          <select
            onChange={(e) => {
              const saved = savedMappings.find(m => m.id === e.target.value);
              if (saved) setMapping(saved.mapping);
            }}
            className="w-full border rounded p-2"
          >
            <option value="">Manual...</option>
            {savedMappings.map(m => (
              <option key={m.id} value={m.id}>
                {m.name} (usado {m.use_count} veces)
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Grid de mapeo */}
      <div className="space-y-3">
        {detectedColumns.map((excelCol, idx) => (
          <div key={idx} className="flex items-center gap-4 p-3 border rounded">
            <div className="flex-1">
              <div className="font-medium">{excelCol}</div>
              <div className="text-sm text-gray-500">
                Ej: {sampleData[0]?.[excelCol]}
              </div>
            </div>

            <div className="text-2xl">→</div>

            <select
              value={mapping[excelCol] || ''}
              onChange={(e) => setMapping({...mapping, [excelCol]: e.target.value})}
              className="flex-1 border rounded p-2"
            >
              <option value="">Seleccionar...</option>
              {targetFields.map(f => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {/* Vista previa */}
      <div className="mt-6 p-4 bg-gray-50 rounded">
        <h4 className="font-medium mb-2">Vista Previa (3 filas)</h4>
        <table className="w-full text-sm">
          <thead>
            <tr>
              {Object.entries(mapping)
                .filter(([_, target]) => target !== 'ignore')
                .map(([_, target]) => (
                  <th key={target} className="text-left p-2 border-b">
                    {targetFields.find(f => f.value === target)?.label}
                  </th>
                ))}
            </tr>
          </thead>
          <tbody>
            {sampleData.slice(0, 3).map((row, i) => (
              <tr key={i}>
                {Object.entries(mapping)
                  .filter(([_, target]) => target !== 'ignore')
                  .map(([excelCol, target]) => (
                    <td key={target} className="p-2 border-b">
                      {row[excelCol]}
                    </td>
                  ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Guardar configuración */}
      <div className="mt-6 flex items-center gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={!!saveName}
            onChange={(e) => setSaveName(e.target.checked ? 'Mi mapeo' : '')}
          />
          <span className="text-sm">Guardar esta configuración</span>
        </label>

        {saveName && (
          <input
            type="text"
            placeholder="Nombre del mapeo..."
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            className="flex-1 border rounded p-2"
          />
        )}
      </div>

      {/* Botón confirmar */}
      <button
        onClick={() => onConfirm(mapping, saveName || undefined)}
        disabled={!Object.values(mapping).includes('name')}
        className="mt-6 w-full bg-blue-600 text-white py-3 rounded font-medium
                   disabled:bg-gray-300 disabled:cursor-not-allowed"
      >
        {Object.values(mapping).includes('name')
          ? 'Continuar con Importación'
          : 'Debes mapear al menos el campo "Nombre Producto"'}
      </button>
    </div>
  );
}
```

---

## 🚀 Próximos Pasos

1. ✅ **Backend Completo** - LISTO
2. 📝 **Frontend React** - Implementar ColumnMappingStep
3. 🎨 **UX/UI** - Drag & drop visual (opcional)
4. 🤖 **IA (Fase 2)** - GPT-4o-mini para sugerencias avanzadas
5. 📱 **Mobile** - Responsive design
6. 🧪 **Tests E2E** - Cypress/Playwright

---

## 📝 Checklist de Implementación

- [x] Migración DB
- [x] Modelo SQLAlchemy
- [x] Servicio excel_analyzer
- [x] Endpoint /analyze-file
- [x] Endpoints CRUD /column-mappings
- [x] Modificación endpoint /ingest
- [x] Aplicar migración en DB
- [ ] Frontend ColumnMappingStep
- [ ] Integrar en flujo de importación
- [ ] Tests unitarios
- [ ] Documentación usuario final

---

## 🎯 Resultado Final

Con este sistema, el Excel `stock-28-10-20251.xlsx` que tiene:
```
| FORMATO DE COMO APUNTAR LAS COMPRAS |
| chochos |
| Paraiso |
```

Se puede mapear manualmente a:
```
{
  "FORMATO DE COMO APUNTAR LAS COMPRAS": "name"
}
```

Y al importar, se convertirá automáticamente en:
```json
{
  "name": "chochos",
  "status": "OK"
}
```

¡Sin necesidad de que el cliente cambie su formato de Excel! 🎉
