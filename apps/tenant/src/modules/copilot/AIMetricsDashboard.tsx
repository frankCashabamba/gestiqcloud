import React, { useState, useEffect } from 'react'
import api from '../../services/api/client'

interface DailyMetric {
  day: string
  requests: number
  errors: number
  tokens: number
}

interface ModelMetric {
  model: string
  requests: number
  tokens: number
}

interface TaskMetric {
  task: string
  requests: number
}

interface MetricsData {
  period_days: number
  total_requests: number
  total_errors: number
  error_rate: number
  total_tokens: number
  estimated_cost_usd: number
  daily: DailyMetric[]
  by_model: ModelMetric[]
  by_task: TaskMetric[]
}

const TASK_LABELS: Record<string, string> = {
  chat: 'Chat',
  classification: 'Clasificación',
  analysis: 'Análisis',
  generation: 'Generación',
  suggestion: 'Sugerencias',
  extraction: 'Extracción',
}

function StatCard({
  label,
  value,
  sub,
  color = 'blue',
}: {
  label: string
  value: string | number
  sub?: string
  color?: 'blue' | 'red' | 'green' | 'purple' | 'orange'
}) {
  const colors = {
    blue:   'bg-blue-50 border-blue-200 text-blue-700',
    red:    'bg-red-50 border-red-200 text-red-700',
    green:  'bg-green-50 border-green-200 text-green-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
    orange: 'bg-orange-50 border-orange-200 text-orange-700',
  }
  return (
    <div className={`border rounded-lg px-5 py-4 ${colors[color]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm font-medium mt-0.5">{label}</div>
      {sub && <div className="text-xs opacity-70 mt-0.5">{sub}</div>}
    </div>
  )
}

function MiniBarChart({ data, maxVal }: { data: { label: string; value: number; color?: string }[]; maxVal: number }) {
  return (
    <div className="space-y-1.5">
      {data.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="text-xs text-slate-500 w-24 truncate shrink-0">{item.label}</span>
          <div className="flex-1 bg-slate-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${item.color || 'bg-blue-500'}`}
              style={{ width: maxVal > 0 ? `${Math.round((item.value / maxVal) * 100)}%` : '0%' }}
            />
          </div>
          <span className="text-xs font-medium w-10 text-right shrink-0">{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function DailyChart({ daily }: { daily: DailyMetric[] }) {
  if (!daily.length) return <p className="text-sm text-slate-400">Sin datos</p>

  const maxReqs = Math.max(...daily.map((d) => d.requests), 1)
  const items = [...daily].reverse().slice(-14) // last 14 days

  return (
    <div className="space-y-1">
      {items.map((d) => {
        const errorPct = d.requests > 0 ? d.errors / d.requests : 0
        const successPct = 1 - errorPct
        return (
          <div key={d.day} className="flex items-center gap-2">
            <span className="text-xs text-slate-500 w-20 shrink-0">
              {new Date(d.day).toLocaleDateString('es', { day: '2-digit', month: 'short' })}
            </span>
            <div className="flex-1 bg-slate-100 rounded h-4 overflow-hidden flex">
              <div
                className="bg-blue-400 h-full"
                style={{ width: `${Math.round((successPct * d.requests / maxReqs) * 100)}%` }}
                title={`OK: ${d.requests - d.errors}`}
              />
              {d.errors > 0 && (
                <div
                  className="bg-red-400 h-full"
                  style={{ width: `${Math.round((errorPct * d.requests / maxReqs) * 100)}%` }}
                  title={`Errores: ${d.errors}`}
                />
              )}
            </div>
            <span className="text-xs w-8 text-right shrink-0">{d.requests}</span>
          </div>
        )
      })}
      <div className="flex gap-3 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-400 rounded-sm inline-block" /> Exitosos</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-400 rounded-sm inline-block" /> Errores</span>
      </div>
    </div>
  )
}

export default function AIMetricsDashboard() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  const load = (d: number) => {
    setLoading(true)
    api.get(`/api/v1/tenant/ai/metrics?days=${d}`)
      .then((res) => setMetrics(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(days) }, [days])

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-200 rounded w-48" />
          <div className="grid grid-cols-4 gap-3">
            {[1,2,3,4].map((i) => <div key={i} className="h-20 bg-slate-100 rounded" />)}
          </div>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="p-6 text-center text-slate-400">
        <p>No se pudieron cargar las métricas de IA.</p>
        <button onClick={() => load(days)} className="mt-3 text-sm text-blue-600 underline">
          Reintentar
        </button>
      </div>
    )
  }

  const modelMax = Math.max(...metrics.by_model.map((m) => m.requests), 1)
  const taskMax = Math.max(...metrics.by_task.map((t) => t.requests), 1)

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold">Métricas de IA</h1>
          <p className="text-sm text-slate-500">Uso del copilot e IA en tu empresa</p>
        </div>
        <div className="flex gap-2">
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 text-sm rounded border ${
                days === d
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard
          label="Total requests"
          value={metrics.total_requests.toLocaleString()}
          sub={`últimos ${days} días`}
          color="blue"
        />
        <StatCard
          label="Error rate"
          value={`${metrics.error_rate}%`}
          sub={`${metrics.total_errors} errores`}
          color={metrics.error_rate > 10 ? 'red' : 'green'}
        />
        <StatCard
          label="Tokens usados"
          value={metrics.total_tokens.toLocaleString()}
          color="purple"
        />
        <StatCard
          label="Costo estimado"
          value={`$${metrics.estimated_cost_usd}`}
          sub="~$0.002/1K tokens"
          color="orange"
        />
        <StatCard
          label="Promedio/día"
          value={metrics.period_days > 0
            ? Math.round(metrics.total_requests / metrics.period_days).toLocaleString()
            : '0'}
          sub="requests por día"
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily usage chart */}
        <div className="bg-white border rounded-lg p-5">
          <h2 className="text-sm font-semibold mb-4">Requests por día (últimos 14 días)</h2>
          <DailyChart daily={metrics.daily} />
        </div>

        {/* Model breakdown */}
        <div className="bg-white border rounded-lg p-5">
          <h2 className="text-sm font-semibold mb-4">Uso por modelo</h2>
          {metrics.by_model.length === 0 ? (
            <p className="text-sm text-slate-400">Sin datos</p>
          ) : (
            <MiniBarChart
              maxVal={modelMax}
              data={metrics.by_model.map((m) => ({
                label: m.model || 'desconocido',
                value: m.requests,
                color: 'bg-purple-500',
              }))}
            />
          )}
          {metrics.by_model.length > 0 && (
            <div className="mt-4 border-t pt-3 space-y-1">
              {metrics.by_model.map((m) => (
                <div key={m.model} className="flex justify-between text-xs text-slate-500">
                  <span>{m.model || 'desconocido'}</span>
                  <span>{m.tokens.toLocaleString()} tokens</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Task breakdown */}
        <div className="bg-white border rounded-lg p-5">
          <h2 className="text-sm font-semibold mb-4">Uso por tipo de tarea</h2>
          {metrics.by_task.length === 0 ? (
            <p className="text-sm text-slate-400">Sin datos</p>
          ) : (
            <MiniBarChart
              maxVal={taskMax}
              data={metrics.by_task.map((t) => ({
                label: TASK_LABELS[t.task] || t.task,
                value: t.requests,
                color: 'bg-blue-500',
              }))}
            />
          )}
        </div>

        {/* Token consumption trend */}
        <div className="bg-white border rounded-lg p-5">
          <h2 className="text-sm font-semibold mb-4">Tokens consumidos (últimos 14 días)</h2>
          {metrics.daily.length === 0 ? (
            <p className="text-sm text-slate-400">Sin datos</p>
          ) : (
            (() => {
              const items = [...metrics.daily].reverse().slice(-14)
              const maxTok = Math.max(...items.map((d) => d.tokens), 1)
              return (
                <MiniBarChart
                  maxVal={maxTok}
                  data={items.map((d) => ({
                    label: new Date(d.day).toLocaleDateString('es', { day: '2-digit', month: 'short' }),
                    value: d.tokens,
                    color: 'bg-orange-400',
                  }))}
                />
              )
            })()
          )}
        </div>
      </div>

      <p className="text-xs text-slate-400">
        * El costo estimado es aproximado ($0.002/1K tokens). El costo real depende del proveedor y modelo utilizado.
      </p>
    </div>
  )
}
