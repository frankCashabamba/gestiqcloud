import React, { useState, useEffect } from 'react'
import { useToast } from '../../shared/toast'
import {
  querySalesByMonth,
  queryTopProducts,
  queryLowStock,
  queryPaymentMovements,
  getSuggestions,
  QueryResult,
  SuggestionsResult,
} from './services'

export default function CopilotDashboard() {
  const { error: showError } = useToast()
  const [loading, setLoading] = useState(false)
  const [salesMonth, setSalesMonth] = useState<QueryResult | null>(null)
  const [topProducts, setTopProducts] = useState<QueryResult | null>(null)
  const [lowStock, setLowStock] = useState<QueryResult | null>(null)
  const [payments, setPayments] = useState<QueryResult | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestionsResult | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [sales, top, stock, pay, suggestions] = await Promise.all([
        querySalesByMonth().catch(() => null),
        queryTopProducts().catch(() => null),
        queryLowStock(5).catch(() => null),
        queryPaymentMovements().catch(() => null),
        getSuggestions().catch(() => null),
      ])
      setSalesMonth(sales)
      setTopProducts(top)
      setLowStock(stock)
      setPayments(pay)
      setSuggestions(suggestions)
    } catch {
      showError('Error cargando datos de Copilot')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">🤖 AI Copilot</h1>
        <button
          onClick={loadData}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Actualizando...' : 'Actualizar'}
        </button>
      </div>

      {/* Sugerencias principales */}
      {suggestions && suggestions.suggestions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {suggestions.suggestions.map((suggestion, idx) => (
            <SuggestionCard key={idx} suggestion={suggestion} />
          ))}
        </div>
      )}

      {/* Grid de datos principal */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {salesMonth && (
          <Card title={salesMonth.cards[0]?.title || 'Ventas por Mes'} insights={salesMonth.ai_insights}>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-64">
              {JSON.stringify(salesMonth.cards[0]?.series, null, 2)}
            </pre>
          </Card>
        )}

        {topProducts && (
          <Card title={topProducts.cards[0]?.title || 'Productos Top'} insights={topProducts.ai_insights}>
            <div className="space-y-2">
              {topProducts.cards[0]?.data?.slice(0, 5).map((item: any, idx: number) => (
                <div key={idx} className="flex justify-between text-sm">
                  <span>{item.name || item.producto || `Item ${idx + 1}`}</span>
                  <span className="font-bold">${formatMoney(item?.importe)}</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {lowStock && (
          <Card title={lowStock.cards[0]?.title || 'Stock Bajo'} insights={lowStock.ai_insights}>
            <div className="space-y-2">
              {lowStock.cards[0]?.data?.slice(0, 5).map((item: any, idx: number) => (
                <div key={idx} className="text-sm text-red-600">
                  {item.almacen}: {item.qty} unidades
                </div>
              ))}
            </div>
          </Card>
        )}

        {payments && (
          <Card title={payments.cards[0]?.title || 'Cobros/Pagos'} insights={payments.ai_insights}>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-64">
              {JSON.stringify(payments.cards[0]?.data, null, 2)}
            </pre>
          </Card>
        )}
      </div>

      {/* Footer con info técnica */}
      <div className="text-xs text-gray-500 space-y-1">
        {salesMonth?.ai_model && <p>🤖 Modelo IA: {salesMonth.ai_model}</p>}
        {suggestions?.generated_at && <p>⏱️ Sugerencias generadas: {new Date(suggestions.generated_at).toLocaleString()}</p>}
        {salesMonth?.sql && <p>📊 SQL: {salesMonth.sql}</p>}
      </div>
    </div>
  )
}

function formatMoney(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) return value.toFixed(2)
  if (typeof value === 'string') {
    const normalized = value.replace(',', '.').trim()
    const parsed = Number(normalized)
    if (Number.isFinite(parsed)) return parsed.toFixed(2)
  }
  return '0.00'
}

function Card({
  title,
  children,
  insights,
}: {
  title: string
  children: React.ReactNode
  insights?: any
}) {
  const [showInsights, setShowInsights] = React.useState(false)

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        {insights && (
          <button
            onClick={() => setShowInsights(!showInsights)}
            className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
          >
            {showInsights ? 'Datos' : '💡 Insights'}
          </button>
        )}
      </div>
      
      {showInsights && insights ? (
        <InsightsPanel insights={insights} />
      ) : (
        children
      )}
    </div>
  )
}

function InsightsPanel({ insights }: { insights: any }) {
  return (
    <div className="space-y-3">
      {insights.findings && insights.findings.length > 0 && (
        <div>
          <h3 className="font-semibold text-sm text-gray-700">📌 Hallazgos Clave</h3>
          <ul className="list-disc list-inside text-sm text-gray-600 space-y-1 mt-1">
            {insights.findings.map((finding: string, idx: number) => (
              <li key={idx}>{finding}</li>
            ))}
          </ul>
        </div>
      )}

      {insights.trends && insights.trends.length > 0 && (
        <div>
          <h3 className="font-semibold text-sm text-gray-700">📈 Tendencias</h3>
          <ul className="list-disc list-inside text-sm text-gray-600 space-y-1 mt-1">
            {insights.trends.map((trend: string, idx: number) => (
              <li key={idx}>{trend}</li>
            ))}
          </ul>
        </div>
      )}

      {insights.recommendations && insights.recommendations.length > 0 && (
        <div>
          <h3 className="font-semibold text-sm text-gray-700">✨ Recomendaciones</h3>
          <ul className="list-disc list-inside text-sm text-green-600 space-y-1 mt-1">
            {insights.recommendations.map((rec: string, idx: number) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {insights.alerts && insights.alerts.length > 0 && (
        <div>
          <h3 className="font-semibold text-sm text-gray-700">🚨 Alertas</h3>
          <div className="space-y-1 mt-1">
            {insights.alerts.map((alert: any, idx: number) => (
              <div key={idx} className="text-sm text-red-600">
                ⚠️ {alert.message || alert}
              </div>
            ))}
          </div>
        </div>
      )}

      {insights.raw && (
        <div className="text-xs text-gray-500 pt-2 border-t">
          <p className="font-mono">{insights.raw}</p>
        </div>
      )}
    </div>
  )
}

function SuggestionCard({ suggestion }: { suggestion: any }) {
  const priorityColor = {
    high: 'bg-red-50 border-red-200 text-red-900',
    medium: 'bg-yellow-50 border-yellow-200 text-yellow-900',
    low: 'bg-blue-50 border-blue-200 text-blue-900',
  }[suggestion.priority] || 'bg-gray-50 border-gray-200'

  const priorityIcon = {
    high: '🔴',
    medium: '🟡',
    low: '🟢',
  }[suggestion.priority] || '⚪'

  return (
    <div className={`border rounded-lg p-4 ${priorityColor}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-sm">
            {priorityIcon} {suggestion.type === 'inventory' && 'Stock'}
            {suggestion.type === 'sales' && 'Ventas'}
            {suggestion.type === 'finance' && 'Finanzas'}
          </h3>
          <p className="text-sm mt-2">{suggestion.content}</p>
          {suggestion.count && (
            <p className="text-xs font-mono mt-1">({suggestion.count} items)</p>
          )}
        </div>
      </div>
      {suggestion.action && (
        <button className="text-xs mt-3 px-2 py-1 bg-white rounded hover:bg-gray-100 opacity-70">
          {suggestion.action}
        </button>
      )}
    </div>
  )
}
