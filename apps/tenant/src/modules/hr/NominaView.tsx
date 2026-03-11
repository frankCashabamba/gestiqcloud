import React, { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Banknote, CheckCircle2, Coins, RefreshCcw, Users, Wallet } from 'lucide-react'
import { GcPageHeader } from '@ui'
import { useNomina } from './hooks/useNomina'
import './hr.css'

function endOfMonth(month: string) {
  const [year, monthNumber] = month.split('-').map(Number)
  if (!year || !monthNumber) return ''
  return new Date(year, monthNumber, 0).toISOString().slice(0, 10)
}

function formatMoney(value: string) {
  const amount = Number(value || 0)
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
  }).format(amount)
}

const statusTone: Record<string, { bg: string; color: string }> = {
  DRAFT: { bg: '#f3f4f6', color: '#111827' },
  CONFIRMED: { bg: '#dbeafe', color: '#1d4ed8' },
  APPROVED: { bg: '#dbeafe', color: '#1d4ed8' },
  PAID: { bg: '#dcfce7', color: '#166534' },
  CANCELLED: { bg: '#fee2e2', color: '#991b1b' },
}

export default function NominaView() {
  const { t } = useTranslation(['hr'])
  const { recibos, loading, submitting, error, reload, generate, confirm, markPaid } = useNomina()
  const [period, setPeriod] = useState(() => new Date().toISOString().slice(0, 7))
  const summary = useMemo(() => {
    const totalEmployees = recibos.reduce((sum, item) => sum + Number(item.total_employees || 0), 0)
    const totalNet = recibos.reduce((sum, item) => sum + Number(item.total_net || 0), 0)
    const pendingRuns = recibos.filter((item) => item.status === 'DRAFT').length
    const paidRuns = recibos.filter((item) => item.status === 'PAID').length
    return { totalEmployees, totalNet, pendingRuns, paidRuns }
  }, [recibos])

  const onGenerate = async () => {
    const payrollDate = endOfMonth(period)
    if (!payrollDate) return
    await generate(period, payrollDate)
  }

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <div className="hr-hero__content">
          <GcPageHeader
            badge="Nomina"
            title={t('hr:payroll.title')}
            subtitle={t('hr:payroll.subtitle')}
            actions={
              <button type="button" onClick={reload} disabled={loading || submitting} className="gc-btn gc-btn--secondary">
                <RefreshCcw size={16} />
                {t('hr:payroll.refresh')}
              </button>
            }
          />
        </div>

        <div className="hr-toolbar" style={{ marginTop: '1.25rem', background: 'rgba(255,255,255,0.82)' }}>
          <div className="hr-table-meta">
            <div className="hr-record-cell">
              <span className="hr-record-cell__title">Generacion de periodo</span>
              <span className="hr-record-cell__meta">
                Crea la corrida mensual y deja las acciones de confirmacion y pago listas para el cierre.
              </span>
            </div>
          </div>

          <div className="hr-toolbar-grid">
            <label className="hr-field">
              <span className="hr-field__label">{t('hr:payroll.periodToGenerate')}</span>
              <input
                type="month"
                value={period}
                onChange={(event) => setPeriod(event.target.value)}
                className="gc-input"
              />
            </label>

            <div className="hr-field" style={{ alignSelf: 'end' }}>
              <button type="button" onClick={onGenerate} disabled={submitting} className="gc-btn gc-btn--primary">
                <Wallet size={16} />
                {submitting ? t('hr:payroll.generating') : t('hr:payroll.generate')}
              </button>
            </div>
          </div>

          {error ? <div className="gc-alert--error">{error}</div> : null}
        </div>

        <div className="hr-kpi-grid" style={{ marginTop: '1.25rem' }}>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Corridas</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <Banknote size={18} />
              </span>
              {recibos.length}
            </div>
            <div className="hr-kpi-card__hint">Periodos generados y visibles en RRHH.</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Empleados</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <Users size={18} />
              </span>
              {summary.totalEmployees}
            </div>
            <div className="hr-kpi-card__hint">{summary.pendingRuns} corridas siguen en borrador.</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Liquido neto</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <Coins size={18} />
              </span>
              {formatMoney(String(summary.totalNet))}
            </div>
            <div className="hr-kpi-card__hint">{summary.paidRuns} corridas ya se marcaron como pagadas.</div>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="gc-card-muted">{t('hr:payroll.loading')}</div>
      ) : recibos.length === 0 ? (
        <div className="gc-card-muted">
          <div className="hr-record-cell__title">{t('hr:payroll.emptyTitle')}</div>
          <div className="hr-record-cell__meta">{t('hr:payroll.emptyHelp')}</div>
        </div>
      ) : (
        <section className="hr-payroll-grid">
          {recibos.map((payroll) => {
            const tone = statusTone[payroll.status] || statusTone.DRAFT
            return (
              <article key={payroll.id} className="hr-payroll-card">
                <div className="hr-payroll-card__head">
                  <div>
                    <h2 className="hr-payroll-card__title">{payroll.payroll_month}</h2>
                    <p className="hr-payroll-card__subtitle">
                      {t('hr:payroll.paymentDateLabel')}: {payroll.payroll_date}
                    </p>
                  </div>
                  <span
                    className="hr-badge"
                    style={{
                      background: tone.bg,
                      color: tone.color,
                      borderColor: tone.bg,
                    }}
                  >
                    <CheckCircle2 size={13} />
                    {t(`hr:payroll.statuses.${payroll.status}`, { defaultValue: payroll.status })}
                  </span>
                </div>

                <div className="hr-payroll-card__metrics">
                  <div className="hr-payroll-card__metric">
                    <div className="hr-payroll-card__metric-label">{t('hr:payroll.totalEmployees')}</div>
                    <div className="hr-payroll-card__metric-value">{payroll.total_employees}</div>
                  </div>
                  <div className="hr-payroll-card__metric">
                    <div className="hr-payroll-card__metric-label">{t('hr:payroll.totalGross')}</div>
                    <div className="hr-payroll-card__metric-value">{formatMoney(payroll.total_gross)}</div>
                  </div>
                  <div className="hr-payroll-card__metric">
                    <div className="hr-payroll-card__metric-label">{t('hr:payroll.totalDeductions')}</div>
                    <div className="hr-payroll-card__metric-value">{formatMoney(payroll.total_deductions)}</div>
                  </div>
                  <div className="hr-payroll-card__metric">
                    <div className="hr-payroll-card__metric-label">{t('hr:payroll.netTotal')}</div>
                    <div className="hr-payroll-card__metric-value">{formatMoney(payroll.total_net)}</div>
                  </div>
                </div>

                <div className="hr-actions-row">
                  {payroll.status === 'DRAFT' ? (
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => confirm(payroll.id)}
                      className="gc-btn gc-btn--primary"
                    >
                      {t('hr:payroll.confirm')}
                    </button>
                  ) : null}
                  {(payroll.status === 'CONFIRMED' || payroll.status === 'APPROVED') ? (
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => markPaid(payroll.id)}
                      className="gc-btn gc-btn--secondary"
                    >
                      {t('hr:payroll.markPaid')}
                    </button>
                  ) : null}
                </div>
              </article>
            )
          })}
        </section>
      )}
    </div>
  )
}
