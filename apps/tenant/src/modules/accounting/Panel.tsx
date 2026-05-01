import React from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { MovimientoTable } from './components/MovimientoTable'
import { useMovimientos } from './hooks/useMovimientos'

const NAV_LINKS = [
  { to: 'dashboard', labelKey: 'accounting.nav.dashboard' },
  { to: 'movimientos', labelKey: 'accounting.nav.transactions' },
  { to: 'libro-diario', labelKey: 'accounting.nav.journal' },
  { to: 'libro-mayor', labelKey: 'accounting.nav.generalLedger' },
  { to: 'pyl', labelKey: 'accounting.nav.profitLoss' },
  { to: 'balance', labelKey: 'accounting.nav.balanceSheet' },
  { to: 'plan-contable', labelKey: 'accounting.nav.chartOfAccounts' },
  { to: 'pos-config', labelKey: 'accounting.nav.posConfig' },
  { to: 'pos-payment-methods', labelKey: 'accounting.nav.paymentMethods' },
]

export function MovimientosPage() {
  const { t } = useTranslation()
  const { asientos, loading, error } = useMovimientos()
  if (loading) {
    return <div className="p-4 text-sm text-gray-500">{t('accounting.loadingTransactions')}</div>
  }
  if (error) {
    return (
      <div className="m-4 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }
  return <MovimientoTable asientos={asientos} />
}

export default function ContabilidadPanel() {
  const { t } = useTranslation()
  const { empresa, mod } = useParams()
  const base = `/${empresa}/${mod}`
  return (
    <div className="contabilidad-panel md:flex gap-6 p-4">
      <nav className="md:w-64 mb-4 md:mb-0">
        <h2 className="text-lg font-semibold mb-3">{t('modules.accounting')}</h2>
        <ul className="space-y-2">
          {NAV_LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={`${base}/${link.to}`}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded ${isActive ? 'bg-blue-100 text-blue-800 font-medium' : 'hover:bg-gray-100'}`
                }
              >
                {t(link.labelKey)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex-1">
        <Outlet />
      </div>
    </div>
  )
}
