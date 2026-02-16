/**
 * AIProviderBadge.tsx
 * 
 * Muestra un badge visual indicando:
 * - Proveedor IA usado (Ollama, OVHCloud, OpenAI, Azure, Local)
 * - Nivel de confianza
 * - Si fue mejorado con IA
 * 
 * Uso:
 * <AIProviderBadge 
 *   provider="ovhcloud" 
 *   confidence={0.95} 
 *   enhanced={true}
 * />
 */

import React from 'react'

interface AIProviderBadgeProps {
  provider?: string | null
  confidence?: number
  enhanced?: boolean
  showIcon?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

/**
 * Mapeo de colores por provider
 */
const PROVIDER_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  ollama: {
    bg: 'bg-blue-50 border-blue-200',
    text: 'text-blue-700',
    icon: '🦙',
  },
  ovhcloud: {
    bg: 'bg-purple-50 border-purple-200',
    text: 'text-purple-700',
    icon: '☁️',
  },
  openai: {
    bg: 'bg-green-50 border-green-200',
    text: 'text-green-700',
    icon: '🤖',
  },
  azure: {
    bg: 'bg-indigo-50 border-indigo-200',
    text: 'text-indigo-700',
    icon: '⛅',
  },
  local: {
    bg: 'bg-gray-50 border-gray-200',
    text: 'text-gray-700',
    icon: '💻',
  },
}

const DEFAULT_COLORS = PROVIDER_COLORS.local

/**
 * Tamaños disponibles
 */
const SIZE_CLASSES: Record<string, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
}

/**
 * Componente AIProviderBadge
 * 
 * Ejemplo de uso completo:
 * 
 * ```tsx
 * import { AIProviderBadge } from './AIProviderBadge'
 * 
 * function MyComponent() {
 *   const analysisResult = {
 *     ai_provider: 'ovhcloud',
 *     ai_enhanced: true,
 *     confidence: 0.95
 *   }
 * 
 *   return (
 *     <div className="flex gap-2 items-center">
 *       <h2>Documento clasificado</h2>
 *       <AIProviderBadge
 *         provider={analysisResult.ai_provider}
 *         confidence={analysisResult.confidence}
 *         enhanced={analysisResult.ai_enhanced}
 *         size="md"
 *       />
 *     </div>
 *   )
 * }
 * ```
 */
export function AIProviderBadge({
  provider,
  confidence = 0,
  enhanced = false,
  showIcon = true,
  size = 'md',
  className = '',
}: AIProviderBadgeProps) {
  // Si no hay provider o no fue mejorado con IA, no mostrar nada
  if (!enhanced || !provider) {
    return null
  }

  const colors = PROVIDER_COLORS[provider.toLowerCase()] || DEFAULT_COLORS
  const sizeClass = SIZE_CLASSES[size]

  // Determinar color de confianza
  const confidencePercentage = confidence * 100
  let confidenceColor = 'text-gray-600'
  if (confidencePercentage >= 90) {
    confidenceColor = 'text-green-600 font-semibold'
  } else if (confidencePercentage >= 75) {
    confidenceColor = 'text-blue-600'
  } else if (confidencePercentage >= 60) {
    confidenceColor = 'text-amber-600'
  } else {
    confidenceColor = 'text-rose-600'
  }

  return (
    <div
      className={`
        inline-flex items-center gap-1.5
        border rounded-full
        font-medium
        ${sizeClass}
        ${colors.bg}
        ${colors.text}
        ${className}
      `}
      title={`Clasificado con ${provider} (${confidencePercentage.toFixed(0)}% confianza)`}
    >
      {/* Icon del provider */}
      {showIcon && <span className="text-lg">{colors.icon}</span>}

      {/* Nombre del provider */}
      <span className="capitalize font-semibold">{provider}</span>

      {/* Confianza si está disponible */}
      {confidence > 0 && (
        <span className={confidenceColor}>
          {confidencePercentage.toFixed(0)}%
        </span>
      )}

      {/* Indicador visual de calidad */}
      {confidencePercentage >= 90 && <span className="text-green-500">✓</span>}
    </div>
  )
}

/**
 * Componente auxiliar para mostrar múltiples providers
 */
export function AIProviderList({
  providers,
  currentProvider,
}: {
  providers: Array<{ name: string; confidence: number; isActive: boolean }>
  currentProvider?: string
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {providers.map((p) => (
        <AIProviderBadge
          key={p.name}
          provider={p.name}
          confidence={p.confidence}
          enhanced={p.isActive}
          size="sm"
          className={p.isActive ? 'ring-2 ring-blue-400' : 'opacity-60'}
        />
      ))}
    </div>
  )
}

/**
 * Componente de estado de provider
 */
export function AIProviderStatus({
  provider,
  status,
  latencyMs,
}: {
  provider?: string
  status: 'healthy' | 'degraded' | 'unavailable'
  latencyMs?: number
}) {
  const statusConfig: Record<string, { color: string; label: string }> = {
    healthy: { color: 'text-green-600', label: 'Operativo' },
    degraded: { color: 'text-amber-600', label: 'Degradado' },
    unavailable: { color: 'text-rose-600', label: 'No disponible' },
  }

  const config = statusConfig[status]

  return (
    <div className="flex items-center gap-2 text-sm">
      {provider && (
        <AIProviderBadge
          provider={provider}
          enhanced={status === 'healthy'}
          size="sm"
        />
      )}
      <span className={config.color}>{config.label}</span>
      {latencyMs && (
        <span className="text-gray-500">({latencyMs}ms)</span>
      )}
    </div>
  )
}

export default AIProviderBadge
