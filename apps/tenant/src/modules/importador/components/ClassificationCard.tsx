/**
 * ClassificationCard - Muestra metadata de clasificación IA
 * Sprint 2: Badges visuales con parser, confianza y proveedor
 */
import React from 'react'

interface ClassificationCardProps {
    suggestedParser: string | null
    confidence: number
    aiProvider: string | null
    enhancedByAI: boolean
    parserOverride?: string | null
}

export const ClassificationCard: React.FC<ClassificationCardProps> = ({
    suggestedParser,
    confidence,
    aiProvider,
    enhancedByAI,
    parserOverride
}) => {
    if (!suggestedParser) return null

    // Determinar color de confianza
    const confidenceColor = 
        confidence > 0.8 ? 'bg-green-100 text-green-800 border-green-300' :
        confidence > 0.6 ? 'bg-amber-100 text-amber-800 border-amber-300' :
        'bg-red-100 text-red-800 border-red-300'

    const confidenceLabel =
        confidence > 0.8 ? 'Alta' :
        confidence > 0.6 ? 'Media' :
        'Baja'

    return (
        <div className="classification-card bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-300 rounded-xl p-5 space-y-4 shadow-sm">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">🔍</span>
                    <h4 className="font-bold text-gray-800">Clasificación Detectada</h4>
                </div>
                {parserOverride && (
                    <div className="bg-amber-100 border border-amber-300 text-amber-900 rounded-full px-3 py-1 text-xs font-bold flex items-center gap-1">
                        <span>⚠️</span>
                        <span>OVERRIDE MANUAL</span>
                    </div>
                )}
            </div>

            {/* Badges Grid */}
            <div className="grid grid-cols-3 gap-3">
                {/* Parser Badge */}
                <div className="bg-white border border-blue-200 rounded-lg p-3 text-center">
                    <div className="text-2xl mb-1">📄</div>
                    <div className="text-xs text-gray-600 mb-1">Parser</div>
                    <div className="font-bold text-sm text-blue-700 break-words">
                        {parserOverride ? (
                            <div>
                                <div className="line-through text-gray-400 text-xs">{suggestedParser}</div>
                                <div className="text-amber-700">{parserOverride}</div>
                            </div>
                        ) : (
                            suggestedParser
                        )}
                    </div>
                </div>

                {/* Confidence Badge */}
                <div className={`border-2 rounded-lg p-3 text-center ${confidenceColor}`}>
                    <div className="text-2xl mb-1">📊</div>
                    <div className="text-xs opacity-75 mb-1">Confianza</div>
                    <div className="font-bold text-sm">
                        {Math.round(confidence * 100)}%
                    </div>
                    <div className="text-xs mt-1 opacity-75">{confidenceLabel}</div>
                </div>

                {/* AI Provider Badge */}
                <div className={`${enhancedByAI ? 'bg-purple-50 border-purple-200' : 'bg-gray-50 border-gray-200'} border-2 rounded-lg p-3 text-center`}>
                    <div className="text-2xl mb-1">{enhancedByAI ? '🤖' : '⚙️'}</div>
                    <div className="text-xs text-gray-600 mb-1">Proveedor</div>
                    <div className={`font-bold text-sm ${enhancedByAI ? 'text-purple-700' : 'text-gray-600'}`}>
                        {enhancedByAI ? (aiProvider || 'IA') : 'Heurística'}
                    </div>
                </div>
            </div>

            {/* Info Footer */}
            <div className="text-xs text-gray-600 border-t border-gray-200 pt-3">
                <p className="mb-1">✓ Clasificación automática detectada con análisis del contenido</p>
                {parserOverride && (
                    <p className="text-amber-700 font-semibold">→ Se usará el parser seleccionado manualmente en lugar de la sugerencia automática</p>
                )}
            </div>
        </div>
    )
}
