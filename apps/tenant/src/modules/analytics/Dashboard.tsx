import React, { useEffect, useMemo, useState } from 'react'
import { useCurrency } from '../../hooks/useCurrency'
import KpiCard from './KpiCard'
import { getTenantKpis, type TenantKpis, type TopProduct } from './api'

interface State {
  loading: boolean
  error: string | null
  data: TenantKpis | null
}

function pickNumber(...candidates: Array<number | undefined | null>): number {
  for (const c of candidates) {
    if (typeof c === 'number' && Number.isFinite(c)) return c
  }
  return 0
}

function pickProducts(data: TenantKpis | null): TopProduct[] {
  if (!data) return []
  const list = data.top_products ?? data.top_productos ?? []
  return Array.isArray(list) ? list.slice(0, 5) : []
}

interface BarChartProps {
  data: Array<{ label: string; value: number }>
  ariaLabel: string
}

function BarChart({ data, ariaLabel }: BarChartProps) {
  const max = useMemo(() => Math.max(1, ...data.map(d => d.value || 0)), [data])
  if (!data.length) {
    return <div className="text-sm text-slate-500">Sin datos disponibles</div>
  }
  const width = 320
  const height = 160
  const barW = Math.floor(width / data.length) - 8
  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${width} ${height}`}
      className="w-full max-w-md"
    >
      {data.map((d, i) => {
        const h = Math.max(2, Math.round((d.value / max) * (height - 30)))
        const x = i * (barW + 8) + 4
        const y = height - h - 16
        return (
          <g key={i}>
            <rect
              x={x}
              y={y}
              width={barW}
              height={h}
              rx={4}
              className="fill-indigo-500"
            >
              <title>{`${d.label}: ${d.value}`}</title>
            </rect>
            <text
              x={x + barW / 2}
              y={height - 4}
              textAnchor="middle"
              className="fill-slate-600"
              style={{ fontSize: 10 }}
            >
              {d.label.length > 10 ? `${d.label.slice(0, 9)}…` : d.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default function AnalyticsDashboard() {
  const [state, setState] = useState<State>({ loading: true, error: null, data: null })
  const [sector, setSector] = useState<string>('')
  const { formatCurrency } = useCurrency()

  useEffect(() => {
    let alive = true
    setState(s => ({ ...s, loading: true, error: null }))
    getTenantKpis(sector ? { sector } : {})
      .then(data => {
        if (alive) setState({ loading: false, error: null, data })
      })
      .catch(err => {
        if (!alive) return
        const msg = err?.response?.data?.detail || err?.message || 'Error al cargar KPIs'
        setState({ loading: false, error: String(msg), data: null })
      })
    return () => {
      alive = false
    }
  }, [sector])

  const data = state.data
  const salesBlock = data?.sales_today ?? data?.daily_sales ?? data?.ventas_dia ?? {}
  const salesTotal = pickNumber(salesBlock.total)
  const tickets = pickNumber(salesBlock.tickets, salesBlock.count)
  const avgTicket = pickNumber(salesBlock.average_ticket, salesBlock.ticket_medio)
  const newCustomersMonth = pickNumber(data?.new_customers?.month)
  const monthlyRevenue = pickNumber(data?.monthly_revenue?.current)
  const monthlyTarget = pickNumber(data?.monthly_revenue?.target)
  const products = pickProducts(data)
  const currency = salesBlock.currency || data?.monthly_revenue?.currency || null

  const chartData = useMemo(
    () =>
      products.map(p => ({
        label: p.name,
        value: pickNumber(p.units, p.unidades, p.revenue, p.ingresos),
      })),
    [products],
  )

  return (
    <section className="p-4 md:p-6 space-y-6" aria-labelledby="analytics-heading">
      <header className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 id="analytics-heading" className="text-2xl font-semibold text-slate-900">
            Analítica
          </h1>
          <p className="text-sm text-slate-500">KPIs en tiempo real para tu sector</p>
        </div>
        <label className="text-sm text-slate-600 inline-flex items-center gap-2">
          Sector:
          <select
            className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
            value={sector}
            onChange={e => setSector(e.target.value)}
          >
            <option value="">Auto</option>
            <option value="default">Genérico</option>
            <option value="panaderia">Panadería</option>
            <option value="taller">Taller</option>
            <option value="retail">Retail</option>
            <option value="todoa100">Todo a 100</option>
          </select>
        </label>
      </header>

      {state.error ? (
        <div role="alert" className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">
          {state.error}
        </div>
      ) : null}

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="kpi-grid"
      >
        <KpiCard
          title="Ventas del día"
          icon="💶"
          loading={state.loading}
          value={formatCurrency(salesTotal)}
          hint={`${tickets} tickets${currency ? ` · ${currency}` : ''}`}
        />
        <KpiCard
          title="Ticket medio"
          icon="🧾"
          loading={state.loading}
          value={formatCurrency(avgTicket)}
        />
        <KpiCard
          title="Clientes nuevos (mes)"
          icon="👥"
          loading={state.loading}
          value={newCustomersMonth}
        />
        <KpiCard
          title="Ingresos del mes"
          icon="📈"
          loading={state.loading}
          value={formatCurrency(monthlyRevenue)}
          hint={
            monthlyTarget > 0
              ? `Objetivo: ${formatCurrency(monthlyTarget)}`
              : undefined
          }
          trend={
            monthlyTarget > 0
              ? { value: (monthlyRevenue / monthlyTarget) * 100 - 100, label: 'vs objetivo' }
              : undefined
          }
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900 mb-3">Top productos</h2>
        {state.loading ? (
          <div className="h-40 animate-pulse rounded bg-slate-100" aria-hidden="true" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <BarChart data={chartData} ariaLabel="Ventas por producto" />
            <ul className="text-sm divide-y divide-slate-100">
              {products.length === 0 ? (
                <li className="py-2 text-slate-500">Sin productos destacados</li>
              ) : (
                products.map((p, i) => (
                  <li key={`${p.name}-${i}`} className="flex items-center justify-between py-2">
                    <span className="text-slate-700">{p.name}</span>
                    <span className="font-medium text-slate-900">
                      {pickNumber(p.units, p.unidades)} u ·{' '}
                      {formatCurrency(pickNumber(p.revenue, p.ingresos))}
                    </span>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </div>

      {data?.message ? (
        <p className="text-xs text-slate-500 italic">{data.message}</p>
      ) : null}
    </section>
  )
}
