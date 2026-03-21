import React, { useState, useEffect, useMemo } from 'react'
import { useToast } from '../../shared/toast'
import {
  askCopilot,
  getSuggestions,
  type QueryResult,
  type SuggestionsResult,
  type AIInsights,
} from './services'
import { getCompanySettings, formatCurrency } from '../../services/companySettings'
import type { CompanySettings } from '../../services/companySettings'
import { exportReport, downloadBlob } from '../reports/services'

// ─── helpers ────────────────────────────────────────────────────────────────

function fmtMoney(v: unknown, cs: CompanySettings | null): string {
  const n = typeof v === 'number' ? v : Number(String(v ?? '').replace(',', '.'))
  return Number.isFinite(n) ? formatCurrency(n, cs ?? undefined) : '—'
}

function fmtMonth(raw: string): string {
  try {
    const [y, m] = raw.split('-')
    return new Date(Number(y), Number(m) - 1).toLocaleDateString('es', { month: 'short', year: '2-digit' })
  } catch { return raw }
}

// ─── mini bar chart (svg) ────────────────────────────────────────────────────

function MiniBar({ values, color = '#3b82f6' }: { values: number[]; color?: string }) {
  const max = Math.max(...values, 1)
  const W = 32; const H = 40; const gap = 3
  return (
    <svg width={values.length * (W + gap)} height={H} style={{ display: 'block' }}>
      {values.map((v, i) => {
        const h = Math.max(3, (v / max) * H)
        return (
          <rect
            key={i}
            x={i * (W + gap)}
            y={H - h}
            width={W}
            height={h}
            rx={3}
            fill={i === values.length - 1 ? color : `${color}99`}
          />
        )
      })}
    </svg>
  )
}

// ─── stock bar ───────────────────────────────────────────────────────────────

function StockBar({ qty, threshold = 5 }: { qty: number; threshold?: number }) {
  const pct = Math.min(100, (qty / (threshold * 2)) * 100)
  const color = qty === 0 ? '#ef4444' : qty <= threshold ? '#f59e0b' : '#10b981'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 bg-gray-100 rounded-full h-1.5">
        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono w-6 text-right" style={{ color }}>{qty}</span>
    </div>
  )
}

// ─── insights panel ──────────────────────────────────────────────────────────

function InsightsPanel({ insights }: { insights: AIInsights }) {
  return (
    <div className="mt-3 pt-3 border-t space-y-2 text-sm">
      {insights.findings?.map((f, i) => (
        <div key={i} className="flex gap-2 text-slate-600"><span className="text-blue-400 mt-0.5">•</span>{f}</div>
      ))}
      {insights.recommendations?.map((r, i) => (
        <div key={i} className="flex gap-2 text-green-700"><span className="mt-0.5">→</span>{r}</div>
      ))}
      {insights.alerts?.map((a, i) => (
        <div key={i} className="flex gap-2 text-red-600"><span className="mt-0.5">⚠</span>{typeof a === 'string' ? a : a.message}</div>
      ))}
      {insights.raw && !insights.findings?.length && !insights.recommendations?.length && (
        <p className="text-slate-500 text-xs">{insights.raw}</p>
      )}
    </div>
  )
}

// ─── card wrapper ────────────────────────────────────────────────────────────

function Card({
  title, icon, topic, params, result, onUpdate, children, loading,
}: {
  title: string; icon: string; topic: Parameters<typeof askCopilot>[0]['topic']
  params?: Record<string, any>; result: QueryResult | null
  onUpdate: (r: QueryResult) => void; children: React.ReactNode; loading: boolean
}) {
  const [analyzing, setAnalyzing] = useState(false)
  const [showInsights, setShowInsights] = useState(false)
  const insights = result?.ai_insights

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const r = await askCopilot({ topic, params, with_ai_insights: true })
      onUpdate(r)
      setShowInsights(true)
    } catch { /* silent */ } finally { setAnalyzing(false) }
  }

  return (
    <div className="bg-white border rounded-xl p-5 flex flex-col">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <h2 className="font-semibold text-gray-800 text-sm">{title}</h2>
        </div>
        {result && (
          insights ? (
            <button
              onClick={() => setShowInsights(s => !s)}
              className="text-xs px-2 py-1 rounded bg-purple-50 text-purple-600 hover:bg-purple-100 border border-purple-200"
            >
              {showInsights ? 'Datos' : '✦ Insights'}
            </button>
          ) : (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="text-xs px-2 py-1 rounded bg-slate-50 text-slate-500 hover:bg-slate-100 border border-slate-200 disabled:opacity-50"
            >
              {analyzing ? '…' : '✦ IA'}
            </button>
          )
        )}
      </div>

      {loading ? (
        <div className="flex-1 space-y-2 animate-pulse">
          <div className="h-3 bg-slate-100 rounded w-3/4" />
          <div className="h-3 bg-slate-100 rounded w-1/2" />
          <div className="h-3 bg-slate-100 rounded w-2/3" />
        </div>
      ) : showInsights && insights ? (
        <InsightsPanel insights={insights} />
      ) : (
        <div className="flex-1">{children}</div>
      )}
    </div>
  )
}

// ─── ventas por mes ──────────────────────────────────────────────────────────

function VentasMesCard({ result, cs }: { result: QueryResult | null; cs: CompanySettings | null }) {
  const series = result?.cards[0]?.series ?? []
  const last6 = series.slice(-6)
  const values = last6.map(s => Number(s.total ?? s.importe ?? 0))
  const total = values.reduce((a, b) => a + b, 0)
  const thisMonth = values[values.length - 1] ?? 0
  const prev = values[values.length - 2] ?? 0
  const delta = prev > 0 ? ((thisMonth - prev) / prev) * 100 : null

  if (!series.length) return <p className="text-sm text-slate-400">Sin datos de ventas</p>

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-end">
        <div>
          <p className="text-2xl font-bold text-gray-900">{fmtMoney(thisMonth, cs)}</p>
          <p className="text-xs text-slate-500">Este mes</p>
        </div>
        {delta !== null && (
          <span className={`text-sm font-semibold ${delta >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {delta >= 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <MiniBar values={values} color="#3b82f6" />
      </div>
      <div className="flex gap-1 overflow-x-auto">
        {last6.map((s, i) => (
          <div key={i} className="flex-1 text-center min-w-0">
            <p className="text-xs text-slate-400 truncate">{fmtMonth(s.mes ?? s.month ?? '')}</p>
          </div>
        ))}
      </div>
      <div className="pt-2 border-t flex justify-between text-xs text-slate-500">
        <span>Acumulado {last6.length} meses</span>
        <span className="font-medium text-slate-700">{fmtMoney(total, cs)}</span>
      </div>
    </div>
  )
}

// ─── top productos ───────────────────────────────────────────────────────────

function TopProductosCard({ result, cs }: { result: QueryResult | null; cs: CompanySettings | null }) {
  const data = result?.cards[0]?.data ?? []
  const top5 = data.slice(0, 5)
  const maxVal = Math.max(...top5.map(d => Number(d.importe ?? d.total ?? 0)), 1)

  if (!top5.length) return <p className="text-sm text-slate-400">Sin datos de productos</p>

  return (
    <div className="space-y-2.5">
      {top5.map((item, i) => {
        const val = Number(item.importe ?? item.total ?? 0)
        const pct = (val / maxVal) * 100
        const name = item.name ?? item.producto ?? item.producto_nombre ?? `Producto ${i + 1}`
        return (
          <div key={i} className="space-y-0.5">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-700 truncate max-w-[160px]">
                <span className="text-slate-400 text-xs mr-1.5">#{i + 1}</span>{name}
              </span>
              <span className="text-sm font-semibold text-gray-800">{fmtMoney(val, cs)}</span>
            </div>
            <div className="h-1 bg-slate-100 rounded-full">
              <div className="h-1 rounded-full bg-blue-400" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── stock bajo ──────────────────────────────────────────────────────────────

function StockBajoCard({ result }: { result: QueryResult | null }) {
  const data = result?.cards[0]?.data ?? []
  const threshold = 5

  if (!data.length) {
    return (
      <div className="flex flex-col items-center justify-center py-4 text-center">
        <span className="text-2xl mb-1">✓</span>
        <p className="text-sm font-medium text-green-600">Stock saludable</p>
        <p className="text-xs text-slate-400">Ningún producto bajo el mínimo</p>
      </div>
    )
  }

  const critical = data.filter(d => Number(d.qty ?? d.stock ?? 0) === 0)
  const warning = data.filter(d => Number(d.qty ?? d.stock ?? 0) > 0)

  return (
    <div className="space-y-1">
      {critical.length > 0 && (
        <div className="text-xs font-semibold text-red-500 mb-1.5">Sin stock ({critical.length})</div>
      )}
      {data.slice(0, 6).map((item, i) => {
        const qty = Number(item.qty ?? item.stock ?? 0)
        const name = item.almacen ?? item.producto ?? item.name ?? `Item ${i + 1}`
        return (
          <div key={i} className="flex items-center gap-2">
            <span className="text-xs text-slate-600 truncate w-32">{name}</span>
            <StockBar qty={qty} threshold={threshold} />
          </div>
        )
      })}
      {data.length > 6 && (
        <p className="text-xs text-slate-400 pt-1">+{data.length - 6} más con stock bajo</p>
      )}
    </div>
  )
}

// ─── cobros y pagos ──────────────────────────────────────────────────────────

function CobrosCard({ result, cs }: { result: QueryResult | null; cs: CompanySettings | null }) {
  const raw = result?.cards[0]
  const data = raw?.data ?? raw?.series ?? []

  // Intentar extraer cobros/pagos de distintas estructuras posibles
  const cobros = data.reduce((s: number, d: any) => {
    const v = Number(d.cobros ?? d.ingresos ?? d.income ?? (d.tipo === 'cobro' ? d.monto : 0) ?? 0)
    return s + v
  }, 0)
  const pagos = data.reduce((s: number, d: any) => {
    const v = Number(d.pagos ?? d.egresos ?? d.expense ?? (d.tipo === 'pago' ? d.monto : 0) ?? 0)
    return s + v
  }, 0)
  const net = cobros - pagos

  if (!data.length) return <p className="text-sm text-slate-400">Sin movimientos registrados</p>

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-green-50 rounded-lg p-3">
          <p className="text-xs text-green-600 mb-1">Cobros</p>
          <p className="text-base font-bold text-green-700">{fmtMoney(cobros, cs)}</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3">
          <p className="text-xs text-red-500 mb-1">Pagos</p>
          <p className="text-base font-bold text-red-600">{fmtMoney(pagos, cs)}</p>
        </div>
      </div>
      <div className="flex justify-between items-center pt-1 border-t">
        <span className="text-xs text-slate-500">Balance</span>
        <span className={`text-sm font-bold ${net >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {net >= 0 ? '+' : ''}{fmtMoney(net, cs)}
        </span>
      </div>
      {data.slice(0, 3).map((d: any, i: number) => {
        const rawLabel = d.mes ?? d.fecha ?? d.periodo ?? d.label ?? ''
        const label = rawLabel
          ? (() => { try { return new Date(rawLabel).toLocaleDateString('es', { month: 'short', year: '2-digit' }) } catch { return rawLabel } })()
          : `Período ${i + 1}`
        const c = Number(d.cobros ?? d.ingresos ?? 0)
        const p = Number(d.pagos ?? d.egresos ?? 0)
        if (!c && !p) return null
        return (
          <div key={i} className="flex justify-between text-xs text-slate-500">
            <span className="capitalize">{label}</span>
            <span className="text-green-600">+{fmtMoney(c, cs)}</span>
            <span className="text-red-500">-{fmtMoney(p, cs)}</span>
          </div>
        )
      })}
    </div>
  )
}

// ─── suggestions ─────────────────────────────────────────────────────────────

const PRIORITY_STYLE = {
  high:   { bg: 'bg-red-50 border-red-200',    dot: 'bg-red-400',    label: 'Urgente' },
  medium: { bg: 'bg-amber-50 border-amber-200', dot: 'bg-amber-400',  label: 'Importante' },
  low:    { bg: 'bg-blue-50 border-blue-200',   dot: 'bg-blue-400',   label: 'Sugerencia' },
}

const TYPE_ICON: Record<string, string> = {
  inventory: '📦',
  sales: '📈',
  finance: '💰',
}

function SuggestionsSection({ suggestions, onLoad }: { suggestions: SuggestionsResult | null; onLoad: (s: SuggestionsResult) => void }) {
  const [loading, setLoading] = useState(false)

  const handle = async () => {
    setLoading(true)
    try { onLoad(await getSuggestions()) } catch { /* silent */ } finally { setLoading(false) }
  }

  if (!suggestions) {
    return (
      <div className="border rounded-xl p-5 bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200 flex items-center justify-between">
        <div>
          <p className="font-semibold text-purple-800">Sugerencias con IA</p>
          <p className="text-sm text-purple-600">Analiza tu negocio y recibe recomendaciones personalizadas</p>
        </div>
        <button
          onClick={handle}
          disabled={loading}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 whitespace-nowrap"
        >
          {loading ? 'Analizando…' : 'Generar ahora'}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm font-semibold text-slate-600">Sugerencias IA</p>
        <button onClick={handle} disabled={loading} className="text-xs text-purple-600 hover:underline disabled:opacity-50">
          {loading ? 'Actualizando…' : 'Actualizar'}
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {suggestions.suggestions.map((s, i) => {
          const style = PRIORITY_STYLE[s.priority] ?? PRIORITY_STYLE.low
          return (
            <div key={i} className={`border rounded-xl p-4 ${style.bg}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${style.dot}`} />
                <span className="text-xs font-medium text-slate-500">{style.label}</span>
                <span className="ml-auto">{TYPE_ICON[s.type] ?? '💡'}</span>
              </div>
              <p className="text-sm text-slate-800 leading-snug">{s.content}</p>
              {s.count != null && (
                <p className="text-xs text-slate-500 mt-1">{s.count} elementos</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── export panel ────────────────────────────────────────────────────────────

const EXPORT_REPORTS = [
  { key: 'sales_summary',    icon: '🛒', label: 'Ventas',      hint: 'Ventas del período con totales y productos' },
  { key: 'inventory_status', icon: '📦', label: 'Inventario',  hint: 'Stock actual, valorización y alertas' },
  { key: 'profit_loss',      icon: '💰', label: 'Financiero',  hint: 'Ingresos, gastos y ganancia neta' },
  { key: 'product_margins',  icon: '📈', label: 'Márgenes',    hint: 'Márgenes por producto y categoría' },
]

const FORMAT_EXT: Record<string, string> = { csv: 'csv', excel: 'xlsx', pdf: 'pdf' }

function toDefaultDate(daysAgo: number): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  return d.toISOString().slice(0, 10)
}

function ExportPanel() {
  const [dateFrom, setDateFrom] = useState(() => toDefaultDate(30))
  const [dateTo, setDateTo]     = useState(() => toDefaultDate(0))
  const [loadingKey, setLoadingKey] = useState<string | null>(null)
  const [errorKey, setErrorKey]     = useState<string | null>(null)

  const handleExport = async (reportKey: string, fmt: string) => {
    const key = `${reportKey}-${fmt}`
    setLoadingKey(key)
    setErrorKey(null)
    try {
      const blob = await exportReport({ report_type: reportKey, format: fmt, date_from: dateFrom, date_to: dateTo })
      downloadBlob(blob, `reporte_${reportKey}.${FORMAT_EXT[fmt] ?? fmt}`)
    } catch {
      setErrorKey(key)
    } finally {
      setLoadingKey(null)
    }
  }

  return (
    <div className="space-y-5">
      {/* Date range */}
      <div className="bg-white border rounded-xl p-4 flex flex-wrap gap-4 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500 font-medium">Desde</label>
          <input
            type="date"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500 font-medium">Hasta</label>
          <input
            type="date"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <p className="text-xs text-slate-400 self-end pb-2">El rango aplica a todos los reportes</p>
      </div>

      {/* Report rows */}
      <div className="space-y-3">
        {EXPORT_REPORTS.map(({ key, icon, label, hint }) => (
          <div key={key} className="bg-white border rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <span className="text-xl">{icon}</span>
              <div className="min-w-0">
                <p className="font-medium text-gray-800 text-sm">{label}</p>
                <p className="text-xs text-slate-400 truncate">{hint}</p>
              </div>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              {(['csv', 'excel', 'pdf'] as const).map(fmt => {
                const bkey = `${key}-${fmt}`
                const isLoading = loadingKey === bkey
                const isError   = errorKey === bkey
                return (
                  <button
                    key={fmt}
                    onClick={() => handleExport(key, fmt)}
                    disabled={!!loadingKey}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50
                      ${isError
                        ? 'bg-red-50 text-red-600 border-red-200'
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                      }`}
                  >
                    {isLoading ? '…' : isError ? '!' : fmt.toUpperCase()}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── main ────────────────────────────────────────────────────────────────────

export default function CopilotDashboard() {
  const { error: showError } = useToast()
  const [activeTab, setActiveTab] = useState<'resumen' | 'exportar'>('resumen')
  const [globalLoading, setGlobalLoading] = useState(true)
  const [cs, setCs] = useState<CompanySettings | null>(null)
  const [salesMonth, setSalesMonth] = useState<QueryResult | null>(null)
  const [topProducts, setTopProducts] = useState<QueryResult | null>(null)
  const [lowStock, setLowStock] = useState<QueryResult | null>(null)
  const [payments, setPayments] = useState<QueryResult | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestionsResult | null>(null)

  const load = async () => {
    setGlobalLoading(true)
    try {
      const [sales, top, stock, pay, settings] = await Promise.all([
        askCopilot({ topic: 'ventas_mes', with_ai_insights: false }).catch(() => null),
        askCopilot({ topic: 'top_productos', with_ai_insights: false }).catch(() => null),
        askCopilot({ topic: 'stock_bajo', params: { threshold: 5 }, with_ai_insights: false }).catch(() => null),
        askCopilot({ topic: 'cobros_pagos', with_ai_insights: false }).catch(() => null),
        getCompanySettings().catch(() => null),
      ])
      setSalesMonth(sales)
      setTopProducts(top)
      setLowStock(stock)
      setPayments(pay)
      setCs(settings)
    } catch {
      showError('No se pudieron cargar los datos del copilot')
    } finally {
      setGlobalLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const stockAlert = useMemo(() => {
    const data = lowStock?.cards[0]?.data ?? []
    return data.filter(d => Number(d.qty ?? d.stock ?? 0) === 0).length
  }, [lowStock])

  return (
    <div className="p-4 md:p-6 space-y-5 max-w-5xl">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200">
        {(['resumen', 'exportar'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px
              ${activeTab === tab
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
          >
            {tab === 'resumen' ? 'Resumen' : 'Exportar'}
          </button>
        ))}
      </div>

      {activeTab === 'resumen' && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Resumen del negocio</h1>
              <p className="text-sm text-slate-500">Datos en tiempo real + análisis con IA</p>
            </div>
            <button
              onClick={load}
              disabled={globalLoading}
              className="px-3 py-1.5 border rounded-lg text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              {globalLoading ? 'Cargando…' : '↻ Actualizar'}
            </button>
          </div>

          {/* Alert banner */}
          {stockAlert > 0 && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
              <span className="text-red-500 text-lg">⚠</span>
              <p className="text-sm text-red-700">
                <span className="font-semibold">{stockAlert} producto{stockAlert > 1 ? 's' : ''} sin stock.</span>{' '}
                Revisa el panel de inventario para reponer.
              </p>
            </div>
          )}

          {/* Sugerencias IA */}
          <SuggestionsSection suggestions={suggestions} onLoad={setSuggestions} />

          {/* Data cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card
              title="Ventas por mes"
              icon="📊"
              topic="ventas_mes"
              result={salesMonth}
              onUpdate={setSalesMonth}
              loading={globalLoading}
            >
              <VentasMesCard result={salesMonth} cs={cs} />
            </Card>

            <Card
              title="Productos más vendidos"
              icon="🏆"
              topic="top_productos"
              result={topProducts}
              onUpdate={setTopProducts}
              loading={globalLoading}
            >
              <TopProductosCard result={topProducts} cs={cs} />
            </Card>

            <Card
              title="Stock bajo mínimo"
              icon="📦"
              topic="stock_bajo"
              params={{ threshold: 5 }}
              result={lowStock}
              onUpdate={setLowStock}
              loading={globalLoading}
            >
              <StockBajoCard result={lowStock} />
            </Card>

            <Card
              title="Cobros y pagos"
              icon="💳"
              topic="cobros_pagos"
              result={payments}
              onUpdate={setPayments}
              loading={globalLoading}
            >
              <CobrosCard result={payments} cs={cs} />
            </Card>
          </div>

          <p className="text-xs text-slate-400">
            El botón ✦ IA en cada tarjeta activa un análisis adicional con inteligencia artificial.
          </p>
        </>
      )}

      {activeTab === 'exportar' && (
        <>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Exportar reportes</h1>
              <p className="text-sm text-slate-500">Descarga reportes en CSV, Excel o PDF para el período seleccionado</p>
            </div>
          </div>
          <ExportPanel />
        </>
      )}
    </div>
  )
}
