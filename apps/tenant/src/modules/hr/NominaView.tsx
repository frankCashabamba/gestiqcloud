import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNomina } from './hooks/useNomina'

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

  const onGenerate = async () => {
    const payrollDate = endOfMonth(period)
    if (!payrollDate) return
    await generate(period, payrollDate)
  }

  return (
    <div style={{ padding: 16, display: 'grid', gap: 16 }}>
      <div
        style={{
          background: '#fff',
          border: '1px solid #dbe3f0',
          borderRadius: 16,
          padding: 16,
          boxShadow: '0 12px 32px rgba(15, 23, 42, 0.06)',
          display: 'grid',
          gap: 12,
        }}
      >
        <div>
          <h2 style={{ fontWeight: 700, fontSize: 24, margin: 0 }}>{t('hr:payroll.title')}</h2>
          <p style={{ margin: '6px 0 0', color: '#4b5563' }}>{t('hr:payroll.subtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 13, color: '#374151' }}>{t('hr:payroll.periodToGenerate')}</span>
            <input
              type="month"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              style={{
                border: '1px solid #cbd5e1',
                borderRadius: 10,
                padding: '10px 12px',
                minWidth: 180,
              }}
            />
          </label>
          <button
            type="button"
            onClick={onGenerate}
            disabled={submitting}
            style={{
              border: 0,
              borderRadius: 10,
              padding: '10px 16px',
              background: '#1d4ed8',
              color: '#fff',
              fontWeight: 600,
              cursor: submitting ? 'wait' : 'pointer',
            }}
          >
            {submitting ? t('hr:payroll.generating') : t('hr:payroll.generate')}
          </button>
          <button
            type="button"
            onClick={reload}
            disabled={loading || submitting}
            style={{
              border: '1px solid #cbd5e1',
              borderRadius: 10,
              padding: '10px 16px',
              background: '#fff',
              color: '#111827',
              fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer',
            }}
          >
            {t('hr:payroll.refresh')}
          </button>
        </div>
        {error ? (
          <div
            style={{
              background: '#fef2f2',
              color: '#991b1b',
              border: '1px solid #fecaca',
              borderRadius: 10,
              padding: '10px 12px',
            }}
          >
            {error}
          </div>
        ) : null}
      </div>

      {loading ? (
        <div style={{ color: '#4b5563' }}>{t('hr:payroll.loading')}</div>
      ) : recibos.length === 0 ? (
        <div
          style={{
            background: '#fff',
            border: '1px dashed #cbd5e1',
            borderRadius: 16,
            padding: 24,
            color: '#4b5563',
          }}
        >
          <div style={{ fontWeight: 600, color: '#111827', marginBottom: 6 }}>
            {t('hr:payroll.emptyTitle')}
          </div>
          <div>{t('hr:payroll.emptyHelp')}</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {recibos.map((payroll) => {
            const tone = statusTone[payroll.status] || statusTone.DRAFT
            return (
              <article
                key={payroll.id}
                style={{
                  background: '#fff',
                  border: '1px solid #dbe3f0',
                  borderRadius: 16,
                  padding: 16,
                  boxShadow: '0 12px 32px rgba(15, 23, 42, 0.05)',
                  display: 'grid',
                  gap: 12,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>
                      {payroll.payroll_month}
                    </div>
                    <div style={{ color: '#6b7280', fontSize: 14 }}>
                      {t('hr:payroll.paymentDateLabel')}: {payroll.payroll_date}
                    </div>
                  </div>
                  <span
                    style={{
                      background: tone.bg,
                      color: tone.color,
                      borderRadius: 999,
                      padding: '6px 10px',
                      fontSize: 12,
                      fontWeight: 700,
                      alignSelf: 'start',
                    }}
                  >
                    {t(`hr:payroll.statuses.${payroll.status}`, { defaultValue: payroll.status })}
                  </span>
                </div>

                <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
                  <div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>{t('hr:payroll.totalEmployees')}</div>
                    <div style={{ fontWeight: 700, color: '#111827' }}>{payroll.total_employees}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>{t('hr:payroll.totalGross')}</div>
                    <div style={{ fontWeight: 700, color: '#111827' }}>{formatMoney(payroll.total_gross)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>{t('hr:payroll.totalDeductions')}</div>
                    <div style={{ fontWeight: 700, color: '#111827' }}>{formatMoney(payroll.total_deductions)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>{t('hr:payroll.netTotal')}</div>
                    <div style={{ fontWeight: 700, color: '#111827' }}>{formatMoney(payroll.total_net)}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {payroll.status === 'DRAFT' ? (
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => confirm(payroll.id)}
                      style={{
                        border: 0,
                        borderRadius: 10,
                        padding: '9px 14px',
                        background: '#1d4ed8',
                        color: '#fff',
                        fontWeight: 600,
                      }}
                    >
                      {t('hr:payroll.confirm')}
                    </button>
                  ) : null}
                  {(payroll.status === 'CONFIRMED' || payroll.status === 'APPROVED') ? (
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => markPaid(payroll.id)}
                      style={{
                        border: 0,
                        borderRadius: 10,
                        padding: '9px 14px',
                        background: '#059669',
                        color: '#fff',
                        fontWeight: 600,
                      }}
                    >
                      {t('hr:payroll.markPaid')}
                    </button>
                  ) : null}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
