/**
 * AIHealthIndicator.tsx
 *
 * Componente que muestra el estado de salud del sistema de IA
 * - Provider actual
 * - Estado (healthy/degraded/unavailable)
 * - Latencia
 * - Providers disponibles como fallback
 */

import React, { useEffect, useState } from 'react'
import { useAuth } from '../../../auth/AuthContext'
import { IMPORTS } from '@endpoints/imports'
import { withImportAIProvider } from '../services/aiProviderPreference'

interface AIHealth {
  status: 'healthy' | 'degraded' | 'unavailable'
  provider: string | null
  available_providers: string[]
  latency_ms?: number
}

interface AIHealthIndicatorProps {
  className?: string
  showDetails?: boolean
}

export function AIHealthIndicator({
  className = '',
  showDetails = true,
}: AIHealthIndicatorProps) {
  const { token } = useAuth() as { token: string | null }
  const [health, setHealth] = useState<AIHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function checkHealth() {
      if (!token) {
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        const response = await fetch(
          withImportAIProvider(IMPORTS.public.aiHealth),
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        )

        if (response.ok) {
          const data = await response.json()
          setHealth(data)
          setError(null)
        } else {
          setError('Failed to fetch health')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    checkHealth()

    // Re-check every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [token])

  if (loading || !health) {
    return (
      <div className={`animate-pulse text-gray-400 text-sm ${className}`}>
        🔍 Checking AI health...
      </div>
    )
  }

  if (error) {
    return (
      <div className={`text-rose-600 text-sm ${className}`}>
        ⚠️ AI Health unavailable
      </div>
    )
  }

  const statusIcons: Record<string, string> = {
    healthy: '✅',
    degraded: '⚠️',
    unavailable: '❌',
  }

  const statusColors: Record<string, string> = {
    healthy: 'text-green-600',
    degraded: 'text-amber-600',
    unavailable: 'text-rose-600',
  }

  const status = health.status
  const icon = statusIcons[status]
  const color = statusColors[status]

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Status indicator */}
      <span className={`text-lg ${color}`}>{icon}</span>

      {/* Provider name */}
      {health.provider && (
        <span className="text-sm font-medium capitalize">
          {health.provider}
        </span>
      )}

      {/* Latency */}
      {health.latency_ms && (
        <span className="text-xs text-gray-500">
          {health.latency_ms}ms
        </span>
      )}

      {/* Details dropdown */}
      {showDetails && health.available_providers.length > 1 && (
        <details className="text-xs text-gray-600">
          <summary className="cursor-pointer">({health.available_providers.length} available)</summary>
          <div className="mt-1 pl-2 text-gray-600">
            {health.available_providers.map((p) => (
              <div key={p} className="text-xs">
                {p === health.provider ? '→ ' : '  '} {p}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

export default AIHealthIndicator
