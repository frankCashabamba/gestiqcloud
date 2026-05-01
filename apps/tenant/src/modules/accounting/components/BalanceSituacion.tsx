import React, { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  getBalanceSheetReport,
  type BalanceSheetReport,
  type ReportAccountLine,
} from '../services'

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function SectionTable({
  title,
  lines,
  total,
  titleColor,
  emptyLabel,
}: {
  title: string
  lines: ReportAccountLine[]
  total: number
  titleColor: string
  emptyLabel: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <h3 className={`text-sm font-semibold ${titleColor}`}>{title}</h3>
      {lines.length === 0 ? (
        <p className="text-sm text-gray-400 italic px-1">{emptyLabel}</p>
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {lines.map((l) => (
              <tr key={l.code} className="border-b border-gray-100 last:border-0">
                <td className="py-1.5 text-gray-500 font-mono w-20">{l.code}</td>
                <td className="py-1.5 text-gray-700">{l.name}</td>
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
      )}
    </div>
  )
}

export const BalanceSituacion: React.FC = () => {
  const { t } = useTranslation()

  const today = new Date().toISOString().slice(0, 10)
  const [asOfDate, setAsOfDate] = useState(today)

  const [data, setData] = useState<BalanceSheetReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchReport = useCallback(() => {
    if (!asOfDate) return
    setLoading(true)
    setError(null)
    getBalanceSheetReport(asOfDate)
      .then(setData)
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : t('accounting.errors.loadTransactions')
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [asOfDate, t])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  return (
    <div className="p-4 max-w-2xl space-y-6">
      {/* Header + filtro de fecha */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-3">
        <h2 className="text-lg font-semibold flex-1">
          {t('accounting.bs.title', 'Balance de Situación')}
        </h2>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-gray-500">
            {t('accounting.bs.asOf', 'A fecha')}
          </label>
          <input
            type="date"
            value={asOfDate}
            onChange={(e) => setAsOfDate(e.target.value)}
            className="border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="animate-pulse space-y-3">
          {[0, 1, 2, 3, 4].map((i) => (
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
          {/* Activo */}
          <SectionTable
            title={t('accounting.bs.assets', 'Activo')}
            lines={data.assets}
            total={data.total_assets}
            titleColor="text-blue-700"
            emptyLabel={t('accounting.bs.noAssets', 'Sin activos registrados')}
          />

          {/* Pasivo */}
          <SectionTable
            title={t('accounting.bs.liabilities', 'Pasivo')}
            lines={data.liabilities}
            total={data.total_liabilities}
            titleColor="text-orange-700"
            emptyLabel={t('accounting.bs.noLiabilities', 'Sin pasivos registrados')}
          />

          {/* Patrimonio */}
          <SectionTable
            title={t('accounting.bs.equity', 'Patrimonio')}
            lines={data.equity}
            total={data.total_equity}
            titleColor="text-green-700"
            emptyLabel={t('accounting.bs.noEquity', 'Sin patrimonio registrado')}
          />

          {/* Ecuación contable */}
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <span className="text-sm text-gray-600">
                {t('accounting.bs.totalAssets', 'Total Activo')}
              </span>
              <span className="text-sm font-mono font-semibold text-gray-900">
                {fmt(data.total_assets)}
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <span className="text-sm text-gray-600 pl-4">
                {t('accounting.bs.totalLiabilities', 'Total Pasivo')}
              </span>
              <span className="text-sm font-mono font-medium text-gray-800">
                {fmt(data.total_liabilities)}
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <span className="text-sm text-gray-600 pl-4">
                {t('accounting.bs.totalEquity', 'Total Patrimonio')}
              </span>
              <span className="text-sm font-mono font-medium text-gray-800">
                {fmt(data.total_equity)}
              </span>
            </div>
            <div
              className={`flex items-center justify-between px-5 py-3 ${
                data.balanced ? 'bg-green-50 border-t border-green-200' : 'bg-red-50 border-t border-red-200'
              }`}
            >
              <span className="text-xs text-gray-500">
                {t('accounting.bs.balanced', 'Ecuación contable (Activo = Pasivo + Patrimonio)')}
              </span>
              <span
                className={`text-sm font-bold ${data.balanced ? 'text-green-700' : 'text-red-600'}`}
              >
                {data.balanced
                  ? t('accounting.bs.balancedOk', 'Cuadra')
                  : t('accounting.bs.balancedError', 'No cuadra')}
              </span>
            </div>
          </div>

          <p className="text-xs text-gray-400">
            {t('accounting.pl.currency', 'Moneda')}: {data.currency} ·{' '}
            {t('accounting.bs.asOf', 'A fecha')}: {data.as_of_date}
          </p>
        </>
      )}
    </div>
  )
}
