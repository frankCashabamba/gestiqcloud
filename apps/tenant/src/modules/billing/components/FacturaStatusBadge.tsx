import React from 'react'
import { useTranslation } from 'react-i18next'

export type InvoiceStatus = 'draft' | 'issued' | 'voided' | 'pending_payment' | string | undefined

export default function FacturaStatusBadge({ status }: { status: InvoiceStatus }) {
  const { t } = useTranslation()
  const e = (status || '').toLowerCase()

  const className =
    e === 'issued'
      ? 'bg-green-100 text-green-800'
      : e === 'voided'
      ? 'bg-red-100 text-red-800'
      : e === 'pending_payment'
      ? 'bg-amber-100 text-amber-800'
      : 'bg-slate-100 text-slate-800'

  const label =
    e === 'pending_payment' ? t('billing.status.pending_payment')
    : e === 'issued' ? t('billing.status.issued')
    : e === 'voided' ? t('billing.status.voided')
    : e === 'draft' ? t('billing.status.draft')
    : e ? e.charAt(0).toUpperCase() + e.slice(1) : '-'

  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${className}`}>{label}</span>
  )
}
