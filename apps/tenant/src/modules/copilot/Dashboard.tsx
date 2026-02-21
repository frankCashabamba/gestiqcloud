import React, { useState, useEffect } from 'react'
import { useToast } from '../../shared/toast'
import {
  askCopilot,
  getSuggestions,
  QueryResult,
  SuggestionsResult,
  Topic,
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
      // Load data WITHOUT AI analysis (fast, SQL only)
      const [sales, top, stock, pay] = await Promise.all([
        askCopilot({ topic: 'ventas_mes', with_ai_insights: false }).catch(() => null),
        askCopilot({ topic: 'top_productos', with_ai_insights: false }).catch(() => null),
        askCopilot({ topic: 'stock_bajo', params: { threshold: 5 }, with_ai_insights: false }).catch(() => null),
        askCopilot({ topic: 'cobros_pagos', with_ai_insights: false }).catch(() => null),
      ])
      setSalesMonth(sales)
      setTopProducts(top)
      setLowStock(stock)
      setPayments(pay)
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

      {/* Sugerencias IA (bajo demanda) */}
      <SuggestionsSection suggestions={suggestions} onLoad={setSuggestions} />

      {/* Grid de datos principal */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {salesMonth && (
          <Card
            title={salesMonth.cards[0]?.title || 'Ventas por Mes'}
            topic="ventas_mes"
            result={salesMonth}
            onUpdate={setSalesMonth}
          >
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-64">
              {JSON.stringify(salesMonth.cards[0]?.series, null, 2)}
            </pre>
          </Card>
        )}

        {topProducts && (
          <Card
            title={topProducts.cards[0]?.title || 'Productos Top'}
            topic="top_productos"
            result={topProducts}
            onUpdate={setTopProducts}
          >
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
          <Card
            title={lowStock.cards[0]?.title || 'Stock Bajo'}
            topic="stock_bajo"
            params={{ threshold: 5 }}
            result={lowStock}
            onUpdate={setLowStock}
          >
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
          <Card
            title={payments.cards[0]?.title || 'Cobros/Pagos'}
            topic="cobros_pagos"
            result={payments}
            onUpdate={setPayments}
          >
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

function SuggestionsSection({
  suggestions,
  onLoad,
}: {
  suggestions: SuggestionsResult | null
  onLoad: (s: SuggestionsResult) => void
}) {
  const [loading, setLoading] = useState(false)

  const handleLoad = async () => {
    setLoading(true)
    try {
      const result = await getSuggestions()
      onLoad(result)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  if (!suggestions) {
    return (
      <button
        onClick={handleLoad}
        disabled={loading}
        className="w-full py-3 border-2 border-dashed border-purple-300 rounded-lg text-purple-600 hover:bg-purple-50 disabled:opacity-50"
      >
        {loading ? '⏳ Generando sugerencias IA...' : '💡 Generar sugerencias con IA'}
      </button>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {suggestions.suggestions.map((suggestion, idx) => (
        <SuggestionCard key={idx} suggestion={suggestion} />
      ))}
    </div>
  )
}

function Card({
  title,
  topic,
  params,
  result,
  onUpdate,
  children,
}: {
  title: string
  topic: Topic
  params?: Record<string, any>
  result: QueryResult
  onUpdate: (r: QueryResult) => void
  children: React.ReactNode
}) {
  const [showInsights, setShowInsights] = React.useState(false)
  const [analyzing, setAnalyzing] = React.useState(false)
  const insights = result.ai_insights

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const updated = await askCopilot({ topic, params, with_ai_insights: true })
      onUpdate(updated)
      setShowInsights(true)
    } catch {
      // ignore
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="flex gap-2">
          {insights ? (
            <button
              onClick={() => setShowInsights(!showInsights)}
              className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
            >
              {showInsights ? 'Datos' : '💡 Insights'}
            </button>
          ) : (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 disabled:opacity-50"
            >
              {analyzing ? '⏳ Analizando...' : '🤖 Analizar con IA'}
            </button>
          )}
        </div>
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
    </div>
  )
}
