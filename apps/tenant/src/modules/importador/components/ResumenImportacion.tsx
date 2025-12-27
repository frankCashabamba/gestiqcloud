import React from 'react'
import { ClassificationCard } from './ClassificationCard'

interface ResumenImportacionProps {
  total: number
  mappedCount: number
  fieldCount: number
  docType: string
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
  mappedCount,
  fieldCount,
  docType,
  classificationResult,
  selectedParser,
}: ResumenImportacionProps) {
  const mappingStatus = `${mappedCount} / ${fieldCount}`

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Import summary</h3>

      {classificationResult && (
        <ClassificationCard
          suggestedParser={classificationResult.suggested_parser}
          confidence={classificationResult.confidence}
          aiProvider={classificationResult.ai_provider}
          enhancedByAI={classificationResult.enhanced_by_ai}
          parserOverride={selectedParser}
        />
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-xs text-gray-500 uppercase font-semibold">Rows to import</div>
          <div className="text-lg font-semibold text-gray-800">{total.toLocaleString()}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-xs text-gray-500 uppercase font-semibold">Fields mapped</div>
          <div className="text-lg font-semibold text-gray-800">{mappingStatus}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-xs text-gray-500 uppercase font-semibold">Document type</div>
          <div className="text-lg font-semibold text-gray-800">{docType}</div>
        </div>
      </div>
    </div>
  )
}
