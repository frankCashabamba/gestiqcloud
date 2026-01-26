import React from 'react'
import { useTranslation } from 'react-i18next'
import { useMovimientos } from '../hooks/useMovimientos'

export function LibroDiario() {
  const { t } = useTranslation()
  const { asientos, loading } = useMovimientos()
  if (loading) return <div className="p-4 text-sm text-gray-500">{t('common.loading')}</div>

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-4">{t('accounting.nav.journal')}</h2>
      {asientos.map((a) => (
        <div key={a.id} className="mb-4">
          <h3 className="font-medium">{a.fecha} - {a.concepto}</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th>{t('common.account')}</th>
                <th>{t('common.description')}</th>
                <th>{t('accounting.journalEntries.columns.debit')}</th>
                <th>{t('accounting.journalEntries.columns.credit')}</th>
              </tr>
            </thead>
            <tbody>
              {a.apuntes.map((ap, i) => (
                <tr key={i} className="border-b">
                  <td>{ap.cuenta}</td>
                  <td>{ap.description}</td>
                  <td>{ap.debe.toFixed(2)}</td>
                  <td>{ap.haber.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
