import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getProfitReport } from '../../../services/api/profit-reports'

const toISO = (d: Date) => d.toISOString().split('T')[0]
const addDays = (d: Date, days: number) => new Date(d.getTime() + days * 86400000)

export const PerdidasGanancias: React.FC = () => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reportData, setReportData] = useState<any>(null)

  useEffect(() => {
    const loadReport = async () => {
      try {
        setLoading(true)
        const dateFrom = toISO(addDays(new Date(), -30))
        const dateTo = toISO(new Date())

        const data = await getProfitReport(dateFrom, dateTo)
        setReportData(data)
        setError(null)
      } catch (err: any) {
        setError(err?.message || 'Error loading profit report')
        setReportData(null)
      } finally {
        setLoading(false)
      }
    }

    loadReport()
  }, [])

  if (loading) return <div style={{ padding: 16 }}>{t('accounting.pl.loading')}</div>
  if (error) return <div style={{ padding: 16, color: 'red' }}>Error: {error}</div>
  if (!reportData) return <div style={{ padding: 16 }}>{t('accounting.pl.noData')}</div>

  const { summary } = reportData

  return (
    <div style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff', margin: 16 }}>
      <h2 style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>{t('accounting.pl.title')}</h2>
      <div style={{ display: 'grid', gap: 6, color: '#111827' }}>
        <div>{t('accounting.pl.totalSales')}: $ {summary.total_sales.toFixed(2)}</div>
        <div>{t('accounting.pl.cogs')}: $ {summary.total_cogs.toFixed(2)}</div>
        <div>{t('accounting.pl.grossProfit')}: $ {summary.gross_profit.toFixed(2)}</div>
        <div>{t('accounting.pl.expenses')}: $ {summary.total_expenses.toFixed(2)}</div>
        <div style={{ fontWeight: 600 }}>{t('accounting.pl.netResult')}: $ {summary.net_profit.toFixed(2)}</div>
        <div style={{ fontSize: 12, color: '#666' }}>
          {t('accounting.pl.netMargin')}: {summary.net_margin_pct.toFixed(2)}%
        </div>
      </div>
    </div>
  )
}
