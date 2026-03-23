import React from 'react'
import { useTranslation } from 'react-i18next'

export type EstadoFactura = 'borrador' | 'emitida' | 'anulada' | string | undefined

export default function FacturaStatusBadge({ estado }: { estado: EstadoFactura }) {
  const { t } = useTranslation()
  const e = (estado || '').toLowerCase()

  const className =
    e === 'emitida' || e === 'issued'
      ? 'bg-green-100 text-green-800'
      : e === 'anulada' || e === 'voided'
      ? 'bg-red-100 text-red-800'
      : e === 'pending_payment'
      ? 'bg-amber-100 text-amber-800'
      : 'bg-slate-100 text-slate-800'

  const label =
    e === 'pending_payment' ? t('billing.status.pending_payment')
    : e === 'issued' || e === 'emitida' ? t('billing.status.issued')
    : e === 'voided' || e === 'anulada' ? t('billing.status.voided')
    : e === 'draft' || e === 'borrador' ? t('billing.status.draft')
    : e ? e.charAt(0).toUpperCase() + e.slice(1) : '-'

  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${className}`}>{label}</span>
  )
}
