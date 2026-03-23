import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listGastos, type Gasto } from '../../expenses/services'
import { listVentas, type Venta } from '../../sales/services'

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const CONFIRMED_STATES = new Set(['emitida', 'facturada', 'entregado', 'confirmed', 'invoiced', 'delivered'])

export const PerdidasGanancias: React.FC = () => {
  const { t } = useTranslation()

  const today = new Date().toISOString().slice(0, 10)
  const firstOfYear = `${new Date().getFullYear()}-01-01`
  const [desde, setDesde] = useState(firstOfYear)
  const [hasta, setHasta] = useState(today)

  const [gastos, setGastos] = useState<Gasto[]>([])
  const [ventas, setVentas] = useState<Venta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listVentas(), listGastos()])
      .then(([v, g]) => { setVentas(v); setGastos(g) })
      .catch(() => setError(t('accounting.errors.loadTransactions')))
      .finally(() => setLoading(false))
  }, [])

  const { ventas: filteredVentas, gastos: filteredGastos } = useMemo(() => {
    const inRange = (d: string) => {
      const f = d.slice(0, 10)
      if (desde && f < desde) return false
      if (hasta && f > hasta) return false
      return true
    }
    return {
      ventas: ventas.filter((v) => inRange(v.fecha) && CONFIRMED_STATES.has(v.estado ?? '')),
      gastos: gastos.filter((g) => inRange(g.date)),
    }
  }, [ventas, gastos, desde, hasta])

  const { totalVentas, totalGastos, resultado } = useMemo(() => {
    const totalVentas = filteredVentas.reduce((s, v) => s + (v.total ?? 0), 0)
    const totalGastos = filteredGastos.reduce((s, g) => s + (g.amount ?? 0), 0)
    return { totalVentas, totalGastos, resultado: totalVentas - totalGastos }
  }, [filteredVentas, filteredGastos])

  const margenNeto = totalVentas > 0 ? (resultado / totalVentas) * 100 : 0

  // Desglose de gastos por categoría
  const gastosPorCategoria = useMemo(() => {
    const map: Record<string, number> = {}
    for (const g of filteredGastos) {
      const cat = g.category || t('accounting.dashboard.uncategorized')
      map[cat] = (map[cat] ?? 0) + (g.amount ?? 0)
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1])
  }, [filteredGastos])

  if (loading) {
    return (
      <div className="p-6 animate-pulse space-y-3">
        {[0, 1, 2, 3, 4].map((i) => <div key={i} className="h-6 rounded bg-gray-100" />)}
      </div>
    )
  }

  if (error) {
    return (
      <div className="m-4 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  const rows = [
    { label: t('accounting.pl.totalSales'), value: totalVentas, bold: false, indent: false },
    { label: t('accounting.pl.cogs'), value: -totalGastos, bold: false, indent: true },
    { label: t('accounting.pl.netResult'), value: resultado, bold: true, indent: false },
  ]

  return (
    <div className="p-4 max-w-2xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end gap-3">
        <h2 className="text-lg font-semibold flex-1">{t('accounting.pl.title')}</h2>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-gray-500">{t('common.from')}</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
          />
          <label className="text-gray-500">{t('common.to')}</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Resumen */}
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        {rows.map((row, i) => (
          <div
            key={i}
            className={`flex items-center justify-between px-5 py-3 ${
              row.bold ? 'bg-gray-50 border-t border-gray-200' : 'border-b border-gray-100'
            }`}
          >
            <span className={`text-sm ${row.bold ? 'font-semibold text-gray-900' : 'text-gray-600'} ${row.indent ? 'pl-4' : ''}`}>
              {row.label}
            </span>
            <span className={`text-sm font-mono ${row.bold ? 'font-bold' : 'font-medium'} ${
              row.value < 0 ? 'text-red-600' : 'text-gray-800'
            }`}>
              {row.value < 0 ? `(${fmt(Math.abs(row.value))})` : fmt(row.value)}
            </span>
          </div>
        ))}
        <div className="flex items-center justify-between px-5 py-3 bg-blue-50 border-t border-blue-200">
          <span className="text-xs text-gray-500">{t('accounting.pl.netMargin')}</span>
          <span className={`text-sm font-bold font-mono ${margenNeto >= 0 ? 'text-blue-700' : 'text-red-600'}`}>
            {margenNeto.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Desglose gastos */}
      {gastosPorCategoria.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">{t('accounting.pl.expenseBreakdown')}</h3>
          <div className="space-y-2">
            {gastosPorCategoria.map(([cat, amount]) => (
              <div key={cat} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between text-sm mb-0.5">
                    <span className="text-gray-600 truncate">{cat}</span>
                    <span className="text-gray-900 font-mono font-medium ml-2 shrink-0">{fmt(amount)}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-red-400 rounded-full"
                      style={{ width: `${totalGastos > 0 ? Math.min(100, (amount / totalGastos) * 100) : 0}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs text-gray-400 w-8 text-right shrink-0">
                  {totalGastos > 0 ? `${((amount / totalGastos) * 100).toFixed(0)}%` : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-400">
        {filteredVentas.length} {t('accounting.dashboard.salesCount')} · {filteredGastos.length} {t('accounting.dashboard.expensesCount')}
      </p>
    </div>
  )
}
