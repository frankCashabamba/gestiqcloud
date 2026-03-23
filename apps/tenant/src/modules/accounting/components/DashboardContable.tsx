import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMovimientos } from '../hooks/useMovimientos'
import { listGastos, type Gasto } from '../../expenses/services'
import { listVentas, type Venta } from '../../sales/services'

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

type Period = 'month' | 'year' | 'all'

function periodLabel(p: Period, t: (k: string) => string) {
  if (p === 'month') return t('accounting.dashboard.thisMonth')
  if (p === 'year') return t('accounting.dashboard.thisYear')
  return t('accounting.dashboard.allTime')
}

function inPeriod(dateStr: string, period: Period): boolean {
  if (period === 'all') return true
  const d = dateStr.slice(0, 10)
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  if (period === 'year') return d.startsWith(`${y}`)
  if (period === 'month') return d.startsWith(`${y}-${m}`)
  return true
}

const CONFIRMED_STATES = new Set(['emitida', 'facturada', 'entregado', 'confirmed', 'invoiced', 'delivered'])

export const DashboardContable: React.FC = () => {
  const { t } = useTranslation()
  const { asientos, loading: loadingAsientos } = useMovimientos()

  const [gastos, setGastos] = useState<Gasto[]>([])
  const [ventas, setVentas] = useState<Venta[]>([])
  const [loadingGastos, setLoadingGastos] = useState(true)
  const [loadingVentas, setLoadingVentas] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState<Period>('month')

  useEffect(() => {
    listGastos()
      .then(setGastos)
      .catch(() => setError(t('accounting.errors.loadTransactions')))
      .finally(() => setLoadingGastos(false))

    listVentas()
      .then(setVentas)
      .catch(() => setError(t('accounting.errors.loadTransactions')))
      .finally(() => setLoadingVentas(false))
  }, [])

  const loading = loadingAsientos || loadingGastos || loadingVentas

  const { ingresos, totalGastos, topCategorias } = useMemo(() => {
    const filteredVentas = ventas.filter(
      (v) => inPeriod(v.fecha, period) && CONFIRMED_STATES.has(v.estado ?? ''),
    )
    const filteredGastos = gastos.filter((g) => inPeriod(g.date, period))

    const ingresos = filteredVentas.reduce((s, v) => s + (v.total ?? 0), 0)
    const totalGastos = filteredGastos.reduce((s, g) => s + (g.amount ?? 0), 0)

    const catMap: Record<string, number> = {}
    for (const g of filteredGastos) {
      const cat = g.category || t('accounting.dashboard.uncategorized')
      catMap[cat] = (catMap[cat] ?? 0) + (g.amount ?? 0)
    }
    const topCategorias = Object.entries(catMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)

    return { ingresos, totalGastos, topCategorias }
  }, [ventas, gastos, period])

  const resultado = ingresos - totalGastos
  const margen = ingresos > 0 ? (resultado / ingresos) * 100 : 0

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <div key={i} className="h-24 rounded-xl bg-gray-100" />)}
        </div>
        <div className="h-40 rounded-xl bg-gray-100" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  const kpis = [
    {
      label: t('accounting.dashboard.totalIncome'),
      value: fmt(ingresos),
      color: 'text-green-700',
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: '↑',
    },
    {
      label: t('accounting.dashboard.totalExpenses'),
      value: fmt(totalGastos),
      color: 'text-red-700',
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: '↓',
    },
    {
      label: t('accounting.dashboard.result'),
      value: fmt(resultado),
      sub: `${margen >= 0 ? '+' : ''}${margen.toFixed(1)}% margen`,
      color: resultado >= 0 ? 'text-blue-700' : 'text-red-700',
      bg: resultado >= 0 ? 'bg-blue-50' : 'bg-red-50',
      border: resultado >= 0 ? 'border-blue-200' : 'border-red-200',
      icon: resultado >= 0 ? '=' : '⚠',
    },
  ]

  const quickLinks = [
    { to: '../pyl', label: t('accounting.nav.profitLoss'), icon: '📊' },
    { to: '../libro-diario', label: t('accounting.nav.journal'), icon: '📒' },
    { to: '../movimientos', label: t('accounting.nav.transactions'), icon: '🔄' },
    { to: '../libro-mayor', label: t('accounting.nav.generalLedger'), icon: '📚' },
  ]

  const periods: Period[] = ['month', 'year', 'all']

  return (
    <div className="space-y-6">
      {/* Period selector */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              period === p
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {periodLabel(p, t)}
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className={`rounded-xl border p-5 ${k.bg} ${k.border}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{k.label}</span>
              <span className={`text-lg font-bold ${k.color}`}>{k.icon}</span>
            </div>
            <div className={`text-2xl font-bold ${k.color}`}>{k.value}</div>
            {k.sub && <div className="text-xs text-gray-500 mt-1">{k.sub}</div>}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top expense categories */}
        {topCategorias.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              {t('accounting.dashboard.topExpenses')}
            </h3>
            <div className="space-y-2">
              {topCategorias.map(([cat, amount]) => (
                <div key={cat} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between text-sm mb-0.5">
                      <span className="text-gray-700 truncate">{cat}</span>
                      <span className="text-gray-900 font-medium ml-2 shrink-0">{fmt(amount)}</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-red-400 rounded-full"
                        style={{ width: `${totalGastos > 0 ? Math.min(100, (amount / totalGastos) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0">
                    {totalGastos > 0 ? `${((amount / totalGastos) * 100).toFixed(0)}%` : '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick links */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
            {t('accounting.dashboard.quickAccess')}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {quickLinks.map((ql) => (
              <Link
                key={ql.to}
                to={ql.to}
                className="flex flex-col items-center gap-2 rounded-lg border border-gray-200 bg-white p-4 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
              >
                <span className="text-2xl">{ql.icon}</span>
                <span className="text-center leading-tight">{ql.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-xs text-gray-400">
        {ventas.length} {t('accounting.dashboard.salesCount')} &middot; {gastos.length} {t('accounting.dashboard.expensesCount')} &middot; {t('accounting.dashboard.basedOn', { count: asientos.length })}
      </div>
    </div>
  )
}
