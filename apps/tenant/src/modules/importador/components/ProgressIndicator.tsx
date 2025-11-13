/**
 * Indicador de progreso animado para importaciones
 */

import React from 'react'

interface Props {
    current: number
    total: number
    message: string
    estimatedTimeRemaining?: number
}

export default function ProgressIndicator({
    current,
    total,
    message,
    estimatedTimeRemaining
}: Props) {
    const percentage = total > 0 ? Math.round((current / total) * 100) : 0

    const formatTime = (seconds: number): string => {
        if (seconds < 60) return `${seconds}s`
        const minutes = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${minutes}m ${secs}s`
    }

    return (
        <div className="w-full max-w-2xl mx-auto space-y-3">
            {/* Barra de progreso */}
            <div className="relative">
                <div className="w-full h-8 bg-gray-200 rounded-lg overflow-hidden shadow-inner">
                    <div
                        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 ease-out flex items-center justify-end px-3"
                        style={{ width: `${percentage}%` }}
                    >
                        {percentage > 15 && (
                            <span className="text-white font-semibold text-sm drop-shadow">
                                {percentage}%
                            </span>
                        )}
                    </div>
                </div>

                {/* Porcentaje fuera de la barra si es muy pequeña */}
                {percentage <= 15 && percentage > 0 && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-700 font-semibold text-sm">
                        {percentage}%
                    </span>
                )}
            </div>

            {/* Información de progreso */}
            <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                    <span className="text-gray-700 font-medium">{message}</span>
                </div>

                <span className="text-gray-600">
                    {current.toLocaleString()} / {total.toLocaleString()} filas
                </span>
            </div>

            {/* Tiempo estimado */}
            {estimatedTimeRemaining !== undefined && estimatedTimeRemaining > 0 && (
                <div className="text-center text-sm text-gray-500">
                    ⏱️ Tiempo estimado restante: {formatTime(estimatedTimeRemaining)}
                </div>
            )}

            {/* Animación de puntos suspensivos */}
            <style>{`
        @keyframes dots {
          0%, 20% { content: '.'; }
          40% { content: '..'; }
          60%, 100% { content: '...'; }
        }
      `}</style>
        </div>
    )
}
