import React from 'react'
import { useTranslation } from 'react-i18next'
import { useNomina } from './hooks/useNomina'

export default function NominaView() {
  const { t } = useTranslation(['hr', 'common'])
  const { recibos, loading } = useNomina()

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>{t('hr:payroll.title')}</h2>
      {loading ? (
        <div>{t('hr:payroll.loading')}</div>
      ) : (
        <ul style={{ display: 'grid', gap: 8 }}>
          {recibos.map((r) => (
            <li key={r.id} style={{ padding: 12, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
              {r.empleado} — {r.mes} — $ {r.monto}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
