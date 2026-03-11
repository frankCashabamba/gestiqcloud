import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getErrorMessage, useToast } from '../../shared/toast'
import {
  getProfitReport,
  triggerRecalculation,
  type ProfitReport,
} from '../../services/api/profit-reports'
import {
  formatCurrency as formatCurrencyWithSettings,
  getCompanySettings,
  type CompanySettings,
} from '../../services/companySettings'
import './reportes.css'

const toISO = (value: Date) => value.toISOString().split('T')[0]
const addDays = (value: Date, days: number) => new Date(value.getTime() + days * 86400000)
const formatPct = (value: number) => `${value.toFixed(2)}%`

function formatMoney(value: number, settings?: CompanySettings | null) {
  return formatCurrencyWithSettings(value || 0, settings || undefined)
}

export default function RealProfitReport() {
  const nav = useNavigate()
  const { t } = useTranslation(['reportes', 'common'])
  const { success, error: toastError } = useToast()
  const [companySettings, setCompanySettings] = useState<CompanySettings | null>(null)
  const [dateFrom, setDateFrom] = useState(() => toISO(addDays(new Date(), -30)))
  const [dateTo, setDateTo] = useState(() => toISO(new Date()))
  const [report, setReport] = useState<ProfitReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [recalculating, setRecalculating] = useState(false)

  const loadReport = async (forceRecalculation = false) => {
    if (!dateFrom || !dateTo) {
      return
    }

    try {
      forceRecalculation ? setRecalculating(true) : setLoading(true)

      if (forceRecalculation) {
        await triggerRecalculation(dateFrom, dateTo)
      }

      const data = await getProfitReport(dateFrom, dateTo)
      setReport(data)

      if (forceRecalculation) {
        success(t('reportes:realResult.recalculated'))
      }
    } catch (err) {
      toastError(getErrorMessage(err))
    } finally {
      setLoading(false)
      setRecalculating(false)
    }
  }

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const settings = await getCompanySettings()
        if (mounted) {
          setCompanySettings(settings)
        }
      } catch {
        // Fallback formatting is acceptable here.
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    loadReport()
    // Initial load only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const summary = report?.summary
  const dailyRows = report?.daily || []
  const isPositive = (summary?.net_profit || 0) >= 0

  return (
    <div className="reports-shell">
      <div className="reports-hero">
        <div>
          <h1>{t('reportes:realResult.title')}</h1>
          <p>{t('reportes:realResult.subtitle')}</p>
        </div>
        <div className="reports-filters">
          <div className="field">
            <label>{t('reportes:margins.filters.from')}</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div className="field">
            <label>{t('reportes:margins.filters.to')}</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div className="field" style={{ alignSelf: 'end' }}>
            <button
              onClick={() => loadReport(false)}
              disabled={loading || recalculating}
              style={{
                padding: '10px 18px',
                borderRadius: 10,
                border: 0,
                background: 'var(--reports-accent)',
                color: '#fff',
                fontWeight: 600,
                cursor: loading || recalculating ? 'wait' : 'pointer',
              }}
            >
              {loading ? t('common:loading') : t('reportes:realResult.generate')}
            </button>
          </div>
          <div className="field" style={{ alignSelf: 'end' }}>
            <button
              onClick={() => loadReport(true)}
              disabled={loading || recalculating}
              style={{
                padding: '10px 18px',
                borderRadius: 10,
                border: '1px solid rgba(16,18,19,0.12)',
                background: '#fff',
                color: 'var(--reports-ink)',
                fontWeight: 600,
                cursor: loading || recalculating ? 'wait' : 'pointer',
              }}
            >
              {recalculating
                ? t('reportes:realResult.recalculating')
                : t('reportes:realResult.refresh')}
            </button>
          </div>
        </div>
      </div>

      <div className="tabs">
        <button onClick={() => nav('..')}>Dashboard</button>
        <button onClick={() => nav('../ventas')}>Ventas</button>
        <button onClick={() => nav('../inventario')}>{t('reportes:dashboard.inventory')}</button>
        <button onClick={() => nav('../financiero')}>Financiero</button>
        <button className="active">{t('reportes:realResult.shortTitle')}</button>
        <button onClick={() => nav('../margenes')}>{t('reportes:dashboard.margins')}</button>
      </div>

      {!report && !loading ? (
        <div className="panel muted">{t('reportes:realResult.empty')}</div>
      ) : null}

      {summary ? (
        <>
          <div className="reports-cards">
            <div className="card">
              <span>{t('reportes:realResult.cards.sales')}</span>
              <strong>{formatMoney(summary.total_sales, companySettings)}</strong>
            </div>
            <div className="card">
              <span>{t('reportes:realResult.cards.cogs')}</span>
              <strong>{formatMoney(summary.total_cogs, companySettings)}</strong>
            </div>
            <div className="card">
              <span>{t('reportes:realResult.cards.expenses')}</span>
              <strong>{formatMoney(summary.total_expenses, companySettings)}</strong>
            </div>
            <div className="card highlight">
              <span>{t('reportes:realResult.cards.net')}</span>
              <strong style={{ color: isPositive ? '#16a34a' : '#b13513' }}>
                {formatMoney(summary.net_profit, companySettings)}
              </strong>
            </div>
          </div>

          <div className="reports-grid">
            <div className="panel">
              <h3>{t('reportes:realResult.summaryTitle')}</h3>
              <div className="row">
                <span>{t('reportes:realResult.cards.grossProfit')}</span>
                <strong>{formatMoney(summary.gross_profit, companySettings)}</strong>
              </div>
              <div className="row">
                <span>{t('reportes:realResult.cards.grossMargin')}</span>
                <strong>{formatPct(summary.gross_margin_pct)}</strong>
              </div>
              <div className="row">
                <span>{t('reportes:realResult.cards.netMargin')}</span>
                <strong>{formatPct(summary.net_margin_pct)}</strong>
              </div>
              <div className="row">
                <span>{t('reportes:realResult.cards.orders')}</span>
                <strong>{summary.total_orders}</strong>
              </div>
            </div>
            <div className="panel">
              <h3>{t('reportes:realResult.notesTitle')}</h3>
              <p>{t('reportes:realResult.noteSales')}</p>
              <p>{t('reportes:realResult.noteExpenses')}</p>
              <p>{t('reportes:realResult.notePayroll')}</p>
            </div>
          </div>

          <div className="panel table-panel">
            <table>
              <thead>
                <tr>
                  <th>{t('reportes:realResult.table.date')}</th>
                  <th>{t('reportes:realResult.table.sales')}</th>
                  <th>{t('reportes:realResult.table.cogs')}</th>
                  <th>{t('reportes:realResult.table.expenses')}</th>
                  <th>{t('reportes:realResult.table.net')}</th>
                  <th>{t('reportes:realResult.table.orders')}</th>
                </tr>
              </thead>
              <tbody>
                {dailyRows.map((row) => (
                  <tr key={row.date} className={row.net_profit < 0 ? 'neg' : ''}>
                    <td>{row.date}</td>
                    <td>{formatMoney(row.sales, companySettings)}</td>
                    <td>{formatMoney(row.cogs, companySettings)}</td>
                    <td>{formatMoney(row.expenses, companySettings)}</td>
                    <td>{formatMoney(row.net_profit, companySettings)}</td>
                    <td>{row.orders}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  )
}
