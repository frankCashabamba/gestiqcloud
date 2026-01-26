import React from 'react'
import { useTranslation } from 'react-i18next'
import { useMovimientos } from '../hooks/useMovimientos'
import { agruparPorCuenta } from '../utils/reportesContables'

export function LibroMayor() {
  const { t } = useTranslation()
  const { asientos, loading } = useMovimientos()
  if (loading) return <div className="p-4 text-sm text-gray-500">{t('accounting.generalLedger.loading')}</div>
  const cuentas = agruparPorCuenta(asientos)

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-4">{t('accounting.generalLedger.title')}</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>{t('common.account')}</th>
            <th>{t('accounting.journalEntries.columns.debit')}</th>
            <th>{t('accounting.journalEntries.columns.credit')}</th>
            <th>{t('accounting.generalLedger.columns.balance')}</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(cuentas).map(([cuenta, v]) => {
            const saldo = (v.debe || 0) - (v.haber || 0)
            return (
              <tr key={cuenta} className="border-b">
                <td>{cuenta}</td>
                <td>{v.debe.toFixed(2)}</td>
                <td>{v.haber.toFixed(2)}</td>
                <td>{saldo.toFixed(2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
