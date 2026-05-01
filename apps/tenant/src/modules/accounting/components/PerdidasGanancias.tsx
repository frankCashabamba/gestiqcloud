import React, { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  getProfitLossReport,
  type ProfitLossReport,
  type ReportAccountLine,
} from '../services'

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function AccountTable({
  lines,
  total,
  emptyLabel,
}: {
  lines: ReportAccountLine[]
  total: number
  emptyLabel: string
}) {
  if (lines.length === 0) {
    return <p className="text-sm text-gray-400 italic px-1">{emptyLabel}</p>
  }
  return (
    <table className="w-full text-sm">
      <tbody>
        {lines.map((l) => (
          <tr key={l.code} className="border-b border-gray-100 last:border-0">
            <td className="py-1.5 text-gray-500 font-mono w-20">{l.code}</td>
            <td className="py-1.5 text-gray-700 flex-1">{l.name}</td>
            <td className="py-1.5 text-right font-mono text-gray-900">
              {l.balance < 0 ? `(${fmt(Math.abs(l.balance))})` : fmt(l.balance)}
            </td>
          </tr>
        ))}
        <tr className="border-t border-gray-300 font-semibold">
          <td colSpan={2} className="pt-2 text-gray-700">
            Total
          </td>
          <td
            className={`pt-2 text-right font-mono ${total < 0 ? 'text-red-600' : 'text-gray-900'}`}
          >
            {total < 0 ? `(${fmt(Math.abs(total))})` : fmt(total)}
          </td>
        </tr>
      </tbody>
    </table>
  )
}

export const PerdidasGanancias: React.FC = () => {
  const { t } = useTranslation()

  const today = new Date().toISOString().slice(0, 10)
  const firstOfYear = `${new Date().getFullYear()}-01-01`
  const [desde, setDesde] = useState(firstOfYear)
  const [hasta, setHasta] = useState(today)

  const [data, setData] = useState<ProfitLossReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchReport = useCallback(() => {
    if (!desde || !hasta) return
    setLoading(true)
    setError(null)
    getProfitLossReport(desde, hasta)
      .then(setData)
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : t('accounting.errors.loadTransactions')
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [desde, hasta, t])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  const netResult = data?.net_result ?? 0
  const totalIncome = data?.total_income ?? 0
  const totalExpenses = data?.total_expenses ?? 0
  const margenNeto = totalIncome > 0 ? (netResult / totalIncome) * 100 : 0

  return (
    <div className="p-4 max-w-2xl space-y-6">
      {/* Header + filtros */}
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

      {/* Loading */}
      {loading && (
        <div className="animate-pulse space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-6 rounded bg-gray-100" />
          ))}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {error}
          <button
            onClick={fetchReport}
            className="ml-3 underline text-red-600 hover:text-red-800"
          >
            {t('common.retry', 'Reintentar')}
          </button>
        </div>
      )}

      {/* Datos */}
      {!loading && !error && data && (
        <>
          {/* Ingresos */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
            <h3 className="text-sm font-semibold text-green-700">
              {t('accounting.pl.income', 'Ingresos')}
            </h3>
            <AccountTable
              lines={data.income}
              total={totalIncome}
              emptyLabel={t('accounting.pl.noIncome', 'Sin ingresos en el período')}
            />
          </div>

          {/* Gastos */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
            <h3 className="text-sm font-semibold text-red-700">
              {t('accounting.pl.expenses', 'Gastos')}
            </h3>
            <AccountTable
              lines={data.expenses}
              total={totalExpenses}
              emptyLabel={t('accounting.pl.noExpenses', 'Sin gastos en el período')}
            />
          </div>

          {/* Resumen */}
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <span className="text-sm text-gray-600">
                {t('accounting.pl.totalSales', 'Total ingresos')}
              </span>
              <span className="text-sm font-mono font-medium text-gray-900">
                {fmt(totalIncome)}
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <span className="text-sm text-gray-600 pl-4">
                {t('accounting.pl.cogs', 'Total gastos')}
              </span>
              <span className="text-sm font-mono font-medium text-gray-800">
                ({fmt(totalExpenses)})
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-t border-gray-200">
              <span className="text-sm font-semibold text-gray-900">
                {t('accounting.pl.netResult', 'Resultado neto')}
              </span>
              <span
                className={`text-sm font-bold font-mono ${netResult < 0 ? 'text-red-600' : 'text-gray-900'}`}
              >
                {netResult < 0 ? `(${fmt(Math.abs(netResult))})` : fmt(netResult)}
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-3 bg-blue-50 border-t border-blue-200">
              <span className="text-xs text-gray-500">{t('accounting.pl.netMargin', 'Margen neto')}</span>
              <span
                className={`text-sm font-bold font-mono ${margenNeto >= 0 ? 'text-blue-700' : 'text-red-600'}`}
              >
                {margenNeto.toFixed(1)}%
              </span>
            </div>
          </div>

          <p className="text-xs text-gray-400">
            {t('accounting.pl.currency', 'Moneda')}: {data.currency} ·{' '}
            {t('accounting.pl.period', 'Período')}: {data.date_from} → {data.date_to}
          </p>
        </>
      )}
    </div>
  )
}
