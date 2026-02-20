import React, { useEffect, useState } from 'react'
import { IMPORTS } from '@endpoints/imports'
import { apiFetch } from '../../../lib/http'
import { withImportAIProvider } from '../services/aiProviderPreference'

interface TelemetryMetric {
  date: string
  accuracy: number
  latency: number
  cost: number
  requests: number
  errors: number
}

interface ProviderStat {
  name: string
  requests: number
  accuracy: number
  latency: number
  cost: number
  errors: number
}

interface DashboardStats {
  totalRequests: number
  avgAccuracy: number
  avgLatency: number
  totalCost: number
  errorRate: number
  metrics: TelemetryMetric[]
  providers: ProviderStat[]
}

interface BackendProviderStat {
  requests?: number
  total_requests?: number
  avg_confidence?: number
  avg_time_ms?: number
  total_cost?: number
  errors?: number
}

interface BackendTelemetryResponse {
  total_requests?: number
  totalRequests?: number
  total_cost?: number
  totalCost?: number
  avg_confidence?: number
  avgAccuracy?: number
  avg_time_ms?: number
  avgLatency?: number
  error_rate?: number
  errorRate?: number
  providers?: Record<string, BackendProviderStat>
  metrics?: TelemetryMetric[]
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  return fallback
}

function normalizeTelemetry(data: BackendTelemetryResponse): DashboardStats {
  const providersObj = data.providers || {}
  const providers: ProviderStat[] = Object.entries(providersObj).map(([name, stat]) => {
    const requests = toNumber(stat.requests, toNumber(stat.total_requests))
    const accuracy = toNumber(stat.avg_confidence)
    const latency = toNumber(stat.avg_time_ms)
    const cost = toNumber(stat.total_cost)
    const errors = toNumber(stat.errors)
    return { name, requests, accuracy, latency, cost, errors }
  })

  const totalRequests = toNumber(data.totalRequests, toNumber(data.total_requests))
  const totalErrors = providers.reduce((acc, provider) => acc + provider.errors, 0)
  const derivedErrorRate = totalRequests > 0 ? totalErrors / totalRequests : 0

  return {
    totalRequests,
    avgAccuracy: toNumber(data.avgAccuracy, toNumber(data.avg_confidence)),
    avgLatency: toNumber(data.avgLatency, toNumber(data.avg_time_ms)),
    totalCost: toNumber(data.totalCost, toNumber(data.total_cost)),
    errorRate: toNumber(data.errorRate, toNumber(data.error_rate, derivedErrorRate)),
    metrics: Array.isArray(data.metrics) ? data.metrics : [],
    providers,
  }
}

export const AITelemetryDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        setLoading(true)
        const data = await apiFetch<BackendTelemetryResponse>(
          withImportAIProvider(IMPORTS.public.aiTelemetry),
          {
          method: 'GET',
          }
        )
        setStats(normalizeTelemetry(data))
      } catch (err) {
        console.error('Error fetching telemetry:', err)
        setStats(null)
      } finally {
        setLoading(false)
      }
    }

    fetchTelemetry()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="spinner mb-3" />
          <p>Cargando telemetria...</p>
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="p-4 bg-amber-50 border border-amber-200 rounded">
        <p className="text-amber-800">No hay datos de telemetria disponibles</p>
      </div>
    )
  }

  const getAccuracyColor = (acc: number) => {
    if (acc >= 0.9) return 'text-green-600 bg-green-50'
    if (acc >= 0.7) return 'text-amber-600 bg-amber-50'
    return 'text-red-600 bg-red-50'
  }

  const getLatencyColor = (latency: number) => {
    if (latency < 1000) return 'text-green-600'
    if (latency < 3000) return 'text-amber-600'
    return 'text-red-600'
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">AI Telemetry</h2>
        <p className="text-sm text-gray-600 mt-1">Metricas reales de clasificacion automatica</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-600">Clasificaciones</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalRequests}</p>
        </div>

        <div className={`rounded-lg p-4 shadow-sm border ${getAccuracyColor(stats.avgAccuracy)}`}>
          <p className="text-sm font-medium opacity-75">Precision promedio</p>
          <p className="text-2xl font-bold mt-1">{Math.round(stats.avgAccuracy * 100)}%</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-600">Latencia promedio</p>
          <p className={`text-2xl font-bold mt-1 ${getLatencyColor(stats.avgLatency)}`}>
            {Math.round(stats.avgLatency)}ms
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-600">Costo total</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">${stats.totalCost.toFixed(2)}</p>
        </div>

        <div
          className={`rounded-lg p-4 shadow-sm border ${
            stats.errorRate > 0.05 ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
          }`}
        >
          <p className="text-sm font-medium opacity-75">Tasa de error</p>
          <p className="text-2xl font-bold mt-1">{Math.round(stats.errorRate * 100)}%</p>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-bold mb-4">Desglose por proveedor</h3>
        {stats.providers.length === 0 ? (
          <p className="text-sm text-gray-600">No hay desglose por proveedor disponible.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.providers.map((provider) => (
              <div key={provider.name} className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <h4 className="font-bold text-slate-900 capitalize">{provider.name}</h4>
                <div className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-600">Requests:</span>
                    <span className="font-semibold text-slate-900">{provider.requests}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Precision:</span>
                    <span className="font-semibold text-slate-900">
                      {Math.round(provider.accuracy * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Latencia:</span>
                    <span className={`font-semibold ${getLatencyColor(provider.latency)}`}>
                      {Math.round(provider.latency)}ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Costo:</span>
                    <span className="font-semibold text-slate-900">${provider.cost.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {stats.metrics.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-bold mb-4">Tendencia</h3>
          <div className="space-y-3">
            {stats.metrics.map((metric) => (
              <div key={metric.date} className="flex items-center gap-4">
                <div className="w-24 text-sm text-gray-700">{metric.date}</div>
                <div className="flex-1 bg-gray-200 rounded-full h-5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-green-400 to-green-600 h-full"
                    style={{ width: `${Math.max(metric.accuracy * 100, 3)}%` }}
                  />
                </div>
                <div className="w-24 text-right text-sm text-gray-600">
                  {Math.round(metric.accuracy * 100)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .spinner {
          width: 24px;
          height: 24px;
          border: 3px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  )
}
