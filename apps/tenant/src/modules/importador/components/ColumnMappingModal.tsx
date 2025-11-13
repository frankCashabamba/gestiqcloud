import React, { useState, useEffect } from 'react'

interface ColumnMappingModalProps {
  isOpen: boolean
  onClose: () => void
  detectedColumns: string[]
  sampleData: Record<string, any>[]
  suggestedMapping: Record<string, string>
  savedMappings: SavedMapping[]
  onConfirm: (mapping: Record<string, string>, saveName?: string) => void
  fileName: string
}

interface SavedMapping {
  id: string
  name: string
  description?: string
  mapping: Record<string, string>
  use_count: number
  last_used_at?: string
}

interface TargetField {
  value: string
  label: string
  required?: boolean
  icon?: string
}

const TARGET_FIELDS: TargetField[] = [
  { value: 'name', label: 'Nombre Producto', required: true, icon: '📦' },
  { value: 'precio', label: 'Precio Venta', icon: '💰' },
  { value: 'cantidad', label: 'Stock/Cantidad', icon: '📊' },
  { value: 'categoria', label: 'Categoría', icon: '🏷️' },
  { value: 'codigo', label: 'Código/SKU', icon: '🔢' },
  { value: 'costo', label: 'Costo Compra', icon: '💸' },
  { value: 'proveedor', label: 'Proveedor', icon: '🏭' },
  { value: 'unidad', label: 'Unidad Medida', icon: '📏' },
  { value: 'ignore', label: 'Ignorar columna', icon: '❌' }
]

export default function ColumnMappingModal({
  isOpen,
  onClose,
  detectedColumns,
  sampleData,
  suggestedMapping,
  savedMappings,
  onConfirm,
  fileName
}: ColumnMappingModalProps) {
  const [mapping, setMapping] = useState<Record<string, string>>(suggestedMapping)
  const [saveName, setSaveName] = useState('')
  const [shouldSave, setShouldSave] = useState(false)
  const [selectedSavedMapping, setSelectedSavedMapping] = useState<string>('')
  const [autoConfirming, setAutoConfirming] = useState(false)

  // Actualizar mapping cuando cambian las sugerencias
  useEffect(() => {
    console.log('🔍 ColumnMappingModal - suggestedMapping:', suggestedMapping)
    console.log('🔍 ColumnMappingModal - detectedColumns:', detectedColumns)
    
    // 🎯 Si el mapping tiene "name" y al menos 2 campos más, es bueno
    const mappedFields = Object.values(suggestedMapping).filter(v => v !== 'ignore')
    const hasName = mappedFields.includes('name')
    
    if (hasName && mappedFields.length >= 2) {
      console.log('✅ Mapeo completo detectado, auto-confirmando...')
      setAutoConfirming(true)
      // Auto-confirmar después de 1.5 segundos para que vea la preview
      setTimeout(() => {
        onConfirm(suggestedMapping)
      }, 1500)
    }
    
    setMapping(suggestedMapping)
  }, [suggestedMapping, detectedColumns])

  if (!isOpen) return null

  const handleLoadSavedMapping = (mappingId: string) => {
    const saved = savedMappings.find(m => m.id === mappingId)
    if (saved) {
      setMapping(saved.mapping)
      setSelectedSavedMapping(mappingId)
    }
  }

  const handleConfirm = () => {
    // Validar que name esté mapeado
    const hasName = Object.values(mapping).includes('name')
    if (!hasName) {
      alert('Debes mapear al menos el campo "Nombre Producto"')
      return
    }

    onConfirm(mapping, shouldSave ? saveName : undefined)
  }

  const getMappedFields = () => {
    return Object.entries(mapping).filter(([_, target]) => target !== 'ignore')
  }

  const isFieldMapped = (targetValue: string) => {
    return Object.values(mapping).includes(targetValue)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-white rounded-lg shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Mapeo de Columnas
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Archivo: <span className="font-medium">{fileName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Auto-confirmación banner */}
          {autoConfirming && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  <svg className="w-6 h-6 text-green-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-900">
                    ✅ Mapeo detectado automáticamente
                  </h3>
                  <p className="text-xs text-green-700 mt-1">
                    El sistema detectó correctamente las columnas. Procesando en 1.5 segundos...
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Selector de mapeo guardado */}
          {savedMappings.length > 0 && (
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💾 Cargar configuración guardada:
              </label>
              <select
                value={selectedSavedMapping}
                onChange={(e) => handleLoadSavedMapping(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Manual...</option>
                {savedMappings.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name} {m.use_count > 0 && `(usado ${m.use_count} veces)`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Grid de mapeo */}
          <div className="space-y-3 mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Relaciona las columnas de tu Excel con los campos del sistema:
            </h3>
            
            {detectedColumns.map((excelCol, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors bg-white"
              >
                {/* Columna Excel */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 truncate">
                    {excelCol}
                  </div>
                  <div className="text-sm text-gray-500 truncate mt-1">
                    Ejemplo: <span className="font-mono text-xs">{sampleData[0]?.[excelCol] || '—'}</span>
                  </div>
                </div>

                {/* Arrow */}
                <div className="text-2xl text-gray-400">→</div>

                {/* Campo destino */}
                <div className="flex-1">
                  <select
                    value={mapping[excelCol] || ''}
                    onChange={(e) => setMapping({ ...mapping, [excelCol]: e.target.value })}
                    className={`w-full border rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      mapping[excelCol] === 'name' 
                        ? 'border-green-500 bg-green-50' 
                        : mapping[excelCol] === 'ignore'
                        ? 'border-gray-300 bg-gray-50'
                        : mapping[excelCol]
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300'
                    }`}
                  >
                    <option value="">Seleccionar campo...</option>
                    {TARGET_FIELDS.map(f => (
                      <option 
                        key={f.value} 
                        value={f.value}
                        disabled={f.value !== 'ignore' && isFieldMapped(f.value) && mapping[excelCol] !== f.value}
                      >
                        {f.icon} {f.label} {f.required ? '*' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>

          {/* Vista previa */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Vista Previa (primeras 3 filas)
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-gray-300">
                    {getMappedFields().map(([excelCol, target]) => (
                      <th key={target} className="text-left p-2 font-medium text-gray-700 bg-gray-100">
                        {TARGET_FIELDS.find(f => f.value === target)?.icon}{' '}
                        {TARGET_FIELDS.find(f => f.value === target)?.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sampleData.slice(0, 3).map((row, i) => (
                    <tr key={i} className="border-b border-gray-200 hover:bg-gray-50">
                      {getMappedFields().map(([excelCol, target]) => (
                        <td key={target} className="p-2 text-gray-900 font-mono text-xs">
                          {row[excelCol] || '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Guardar configuración */}
          <div className="mt-6 p-4 bg-amber-50 rounded-lg border border-amber-200">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={shouldSave}
                onChange={(e) => setShouldSave(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">
                💾 Guardar esta configuración para reutilizar
              </span>
            </label>

            {shouldSave && (
              <div className="mt-3">
                <input
                  type="text"
                  placeholder="Ej: Proveedor Lácteos - Mensual"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  autoFocus
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 bg-gray-50 flex items-center justify-between rounded-b-lg">
          <div className="text-sm text-gray-600">
            {Object.values(mapping).includes('name') ? (
              <span className="text-green-600 font-medium flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Listo para continuar
              </span>
            ) : (
              <span className="text-amber-600 font-medium flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Debes mapear "Nombre Producto"
              </span>
            )}
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleConfirm}
              disabled={!Object.values(mapping).includes('name')}
              className="px-6 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Continuar con Importación
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
