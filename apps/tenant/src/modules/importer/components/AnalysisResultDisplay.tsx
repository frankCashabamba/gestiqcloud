/**
 * AnalysisResultDisplay.tsx
 * 
 * Componente para mostrar los resultados del análisis IA
 * Incluye:
 * - Parser sugerido
 * - Confianza
 * - Proveedor IA
 * - Mapeo sugerido
 * - Decision log
 * - Opción de confirmar o rechazar
 */

import React from 'react'
import { AnalyzeResponse } from '../services/analyzeApi'
import { AIProviderBadge } from './AIProviderBadge'

interface AnalysisResultDisplayProps {
  analysis: AnalyzeResponse
  onConfirm?: () => void
  onEdit?: () => void
  loading?: boolean
}

export function AnalysisResultDisplay({
  analysis,
  onConfirm,
  onEdit,
  loading = false,
}: AnalysisResultDisplayProps) {
  const confidencePercentage = (analysis.confidence * 100).toFixed(0)
  const isHighConfidence = analysis.confidence >= 0.8
  const isMediumConfidence = analysis.confidence >= 0.6

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-gradient-to-br from-blue-50 to-transparent">
      {/* Header con resultado principal */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">
            {analysis.suggested_doc_type}
          </h3>
          <p className="text-sm text-gray-600">
            Parser: <span className="font-mono font-medium">{analysis.suggested_parser}</span>
          </p>
        </div>

        {/* Badge de proveedor */}
        <AIProviderBadge
          provider={analysis.ai_provider}
          confidence={analysis.confidence}
          enhanced={analysis.ai_enhanced}
          size="md"
        />
      </div>

      {/* Confianza visual */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Confianza</span>
          <span className={`text-lg font-bold ${
            isHighConfidence ? 'text-green-600' :
            isMediumConfidence ? 'text-amber-600' :
            'text-rose-600'
          }`}>
            {confidencePercentage}%
          </span>
        </div>
        
        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              isHighConfidence ? 'bg-green-500' :
              isMediumConfidence ? 'bg-amber-500' :
              'bg-rose-500'
            }`}
            style={{ width: `${analysis.confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Explicación */}
      {analysis.explanation && (
        <div className="bg-white rounded p-3 text-sm text-gray-700">
          <p className="flex gap-2">
            <span>💭</span>
            <span>{analysis.explanation}</span>
          </p>
        </div>
      )}

      {/* Mapeo sugerido */}
      {analysis.mapping_suggestion && Object.keys(analysis.mapping_suggestion).length > 0 && (
        <div className="bg-white rounded p-3">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Mapeo Sugerido</h4>
          <div className="space-y-1 text-sm">
            {Object.entries(analysis.mapping_suggestion).map(([source, target]) => (
              <div key={source} className="flex items-center justify-between text-gray-700">
                <code className="bg-gray-100 px-2 py-1 rounded text-xs">{source}</code>
                <span className="text-gray-400">→</span>
                <code className="bg-gray-100 px-2 py-1 rounded text-xs">{target}</code>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decision log (expandible) */}
      {analysis.decision_log && analysis.decision_log.length > 0 && (
        <details className="text-xs text-gray-600">
          <summary className="cursor-pointer font-medium hover:text-gray-900">
            🔍 Ver detalles del análisis ({analysis.decision_log.length} pasos)
          </summary>
          <div className="mt-2 space-y-1 pl-4 text-gray-600">
            {analysis.decision_log.map((log, idx) => (
              <div key={idx} className="py-1 border-l border-gray-300 pl-2">
                <div className="font-mono text-gray-700">{log.step}</div>
                {log.confidence && (
                  <div className="text-gray-500">
                    Confianza: {(log.confidence * 100).toFixed(0)}%
                  </div>
                )}
                {log.duration_ms && (
                  <div className="text-gray-500">
                    Tiempo: {log.duration_ms}ms
                  </div>
                )}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Probabilidades de otros parsers */}
      {analysis.probabilities && Object.keys(analysis.probabilities).length > 1 && (
        <details className="text-xs text-gray-600">
          <summary className="cursor-pointer font-medium hover:text-gray-900">
            📊 Otras opciones ({Object.keys(analysis.probabilities).length})
          </summary>
          <div className="mt-2 space-y-1 text-gray-600">
            {Object.entries(analysis.probabilities)
              .sort(([_, a], [__, b]) => b - a)
              .slice(1)
              .map(([parser, prob]) => (
                <div key={parser} className="flex items-center justify-between">
                  <span className="font-mono text-sm">{parser}</span>
                  <span className="text-gray-500">{(prob * 100).toFixed(0)}%</span>
                </div>
              ))}
          </div>
        </details>
      )}

      {/* Advertencia si requiere confirmación */}
      {analysis.requires_confirmation && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm">
          <p className="text-amber-900 flex gap-2">
            <span>⚠️</span>
            <span>
              Confianza moderada. Por favor, revisa el mapeo antes de continuar.
            </span>
          </p>
        </div>
      )}

      {/* Botones de acción */}
      {(onConfirm || onEdit) && (
        <div className="flex gap-2 pt-2 border-t">
          {onEdit && (
            <button
              onClick={onEdit}
              disabled={loading}
              className="flex-1 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 disabled:opacity-50"
            >
              ✏️ Editar Mapeo
            </button>
          )}
          {onConfirm && (
            <button
              onClick={onConfirm}
              disabled={loading}
              className={`flex-1 px-3 py-2 text-sm font-medium text-white rounded disabled:opacity-50 ${
                isHighConfidence
                  ? 'bg-green-600 hover:bg-green-700'
                  : isMediumConfidence
                  ? 'bg-amber-600 hover:bg-amber-700'
                  : 'bg-rose-600 hover:bg-rose-700'
              }`}
            >
              {loading ? '⏳ Procesando...' : '✓ Confirmar'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default AnalysisResultDisplay
