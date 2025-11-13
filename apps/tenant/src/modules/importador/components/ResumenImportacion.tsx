import React from 'react'
import { ClassificationCard } from './ClassificationCard'

interface ResumenImportacionProps {
  total: number
  onBack: () => void
  onImport: () => void
  // Sprint 2: Classification metadata
  classificationResult?: {
    suggested_parser: string
    confidence: number
    ai_provider?: string
    enhanced_by_ai: boolean
  } | null
  selectedParser?: string | null
}

export default function ResumenImportacion({
  total,
  onBack,
  onImport,
  classificationResult,
  selectedParser
}: ResumenImportacionProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Resumen de Importación</h3>

      {/* Sprint 2: Mostrar card de clasificación */}
      {classificationResult && (
        <ClassificationCard
          suggestedParser={classificationResult.suggested_parser}
          confidence={classificationResult.confidence}
          aiProvider={classificationResult.ai_provider}
          enhancedByAI={classificationResult.enhanced_by_ai}
          parserOverride={selectedParser}
        />
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="text-sm text-gray-700">
          <strong>Filas a importar:</strong> {total.toLocaleString()}
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={onBack}>← Volver</button>
        <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded font-semibold" onClick={onImport}>✓ Importar</button>
      </div>
    </div>
  )
}

