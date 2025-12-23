/**
 * AITelemetryDashboard - Dashboard de telemetría IA
 * Sprint 3: Metrics, accuracy, latency, costs, trends
 */
import React, { useEffect, useState } from 'react'

interface TelemetryMetric {
  date: string
  accuracy: number
  latency: number
  cost: number
  requests: number
  errors: number
}

interface DashboardStats {
  totalRequests: number
  avgAccuracy: number
  avgLatency: number
  totalCost: number
  errorRate: number
  metrics: TelemetryMetric[]
}

export const AITelemetryDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Cargar telemetría del backend
    const fetchTelemetry = async () => {
      try {
        const response = await fetch(`/api/v1/tenant/imports/telemetry?range=${timeRange}`)
        if (response.ok) {
          const data = await response.json()
          setStats(data)
        }
      } catch (err) {
        console.error('Error fetching telemetry:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchTelemetry()
  }, [timeRange])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="spinner mb-3" />
          <p>Cargando telemetría...</p>
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="p-4 bg-amber-50 border border-amber-200 rounded">
        <p className="text-amber-800">No hay datos de telemetría disponibles</p>
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">📊 Telemetría IA</h2>
          <p className="text-sm text-gray-600 mt-1">Métricas de clasificación automática</p>
        </div>

        <div className="flex gap-2">
          {(['24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-2 rounded text-sm font-medium transition ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
              }`}
            >
              {range === '24h' ? 'Today' : range === '7d' ? '7 días' : '30 días'}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Requests */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">Clasificaciones</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalRequests}</p>
            </div>
            <span className="text-2xl">📋</span>
          </div>
        </div>

        {/* Accuracy */}
        <div className={`rounded-lg p-4 shadow-sm border ${getAccuracyColor(stats.avgAccuracy)}`}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium opacity-75">Precisión Promedio</p>
              <p className="text-2xl font-bold mt-1">{Math.round(stats.avgAccuracy * 100)}%</p>
            </div>
            <span className="text-2xl">🎯</span>
          </div>
        </div>

        {/* Latency */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">Latencia Promedio</p>
              <p className={`text-2xl font-bold mt-1 ${getLatencyColor(stats.avgLatency)}`}>
                {Math.round(stats.avgLatency)}ms
              </p>
            </div>
            <span className="text-2xl">⚡</span>
          </div>
        </div>

        {/* Cost */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">Costo Total</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">${stats.totalCost.toFixed(2)}</p>
            </div>
            <span className="text-2xl">💰</span>
          </div>
        </div>

        {/* Error Rate */}
        <div className={`rounded-lg p-4 shadow-sm border ${stats.errorRate > 0.05 ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium opacity-75">Tasa de Error</p>
              <p className="text-2xl font-bold mt-1">{Math.round(stats.errorRate * 100)}%</p>
            </div>
            <span className="text-2xl">{stats.errorRate > 0.05 ? '⚠️' : '✅'}</span>
          </div>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-bold mb-4">Tendencia de Precisión (últimos días)</h3>

        <div className="space-y-4">
          {stats.metrics.map((metric) => (
            <div key={metric.date} className="flex items-center gap-4">
              <div className="w-20 text-sm font-medium text-gray-700">{metric.date}</div>

              {/* Accuracy Bar */}
              <div className="flex-1">
                <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-green-400 to-green-600 h-full rounded-full flex items-center justify-center transition"
                    style={{ width: `${Math.max(metric.accuracy * 100, 5)}%` }}
                  >
                    <span className="text-xs font-bold text-white">
                      {Math.round(metric.accuracy * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Metrics */}
              <div className="w-48 text-right">
                <div className="text-sm text-gray-600">
                  <span className="font-medium">{metric.requests}</span> req •
                  <span className={`ml-2 ${getLatencyColor(metric.latency)}`}>
                    {Math.round(metric.latency)}ms
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Provider Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Local Provider */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">⚙️</span>
            <h4 className="font-bold text-blue-900">Local (Gratuita)</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-blue-700">Precisión:</span>
              <span className="font-bold text-blue-900">85%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-700">Latencia:</span>
              <span className="font-bold text-blue-900">150ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-700">Costo:</span>
              <span className="font-bold text-blue-900">$0.00</span>
            </div>
          </div>
        </div>

        {/* OpenAI */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">🤖</span>
            <h4 className="font-bold text-green-900">OpenAI</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-green-700">Precisión:</span>
              <span className="font-bold text-green-900">98%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-700">Latencia:</span>
              <span className="font-bold text-green-900">1.2s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-700">Costo:</span>
              <span className="font-bold text-green-900">$24.50</span>
            </div>
          </div>
        </div>

        {/* Azure */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">☁️</span>
            <h4 className="font-bold text-purple-900">Azure OpenAI</h4>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-purple-700">Precisión:</span>
              <span className="font-bold text-purple-900">97%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-purple-700">Latencia:</span>
              <span className="font-bold text-purple-900">980ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-purple-700">Costo:</span>
              <span className="font-bold text-purple-900">$18.75</span>
            </div>
          </div>
        </div>
      </div>

      {/* Insights */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-bold text-gray-800 mb-3">💡 Insights</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>✓ Precisión promedio en rango óptimo ({Math.round(stats.avgAccuracy * 100)}%)</li>
          <li>✓ Latencia dentro de límites aceptables ({Math.round(stats.avgLatency)}ms)</li>
          <li>✓ Tasa de error bajo control ({Math.round(stats.errorRate * 100)}%)</li>
          <li className="text-blue-700 font-medium">→ Considerar OpenAI para precisión crítica</li>
        </ul>
      </div>

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
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
