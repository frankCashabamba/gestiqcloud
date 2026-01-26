/**
 * EinvoiceStatus - Componente compacto y accesible para mostrar/gestionar el estado de e-factura.
 */
import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getEinvoiceStatus, getEinvoiceStatusColor, sendEinvoice } from '../services'
import type { EinvoiceStatus } from '../services'

interface EinvoiceStatusProps {
  invoiceId: string
  country: 'ES' | 'EC'
  canSend?: boolean
  enabled?: boolean
}

const statusClass = (color: string) =>
  ({
    green: 'bg-green-500/90 text-white',
    yellow: 'bg-amber-500/90 text-white',
    blue: 'bg-blue-500/90 text-white',
    red: 'bg-red-500/90 text-white',
  }[color] ?? 'bg-gray-500/90 text-white')

export default function EinvoiceStatus({ invoiceId, country, canSend = true, enabled = true }: EinvoiceStatusProps) {
  const { t } = useTranslation()
  const [status, setStatus] = useState<EinvoiceStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadStatus = async () => {
    setError(null)
    try {
      setLoading(true)
      const s = await getEinvoiceStatus(invoiceId)
      setStatus(s || null)
    } catch (err: any) {
      setError(t('billing.einvoiceStatus.errorLoading'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!enabled) return
    loadStatus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoiceId, enabled])

  const handleSend = async () => {
    try {
      setSending(true)
      setError(null)
      await sendEinvoice({ invoice_id: invoiceId, country })
      // Re-consulta tras breve espera para que el backend procese el envío
      setTimeout(loadStatus, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || t('billing.einvoiceStatus.errorSending'))
    } finally {
      setSending(false)
    }
  }

  if (loading && !status) {
    return <span className="text-xs text-gray-500">{t('common.loading')}…</span>
  }

  if (!status) {
    const provider = country === 'ES' ? 'Facturae' : 'SRI'
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="text-gray-600">{t('billing.einvoiceStatus.notSent')}</span>
        {canSend && (
          <button
            type="button"
            onClick={handleSend}
            disabled={sending}
            className="px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
          >
            {sending ? t('billing.einvoiceStatus.sending') : t('billing.einvoiceStatus.send', { provider })}
          </button>
        )}
        {error && <span className="text-red-600">{error}</span>}
      </div>
    )
  }

  const badgeColor = statusClass(getEinvoiceStatusColor(status.status))
  const showError = Boolean(status.error_message || error)

  return (
    <div className="flex items-center gap-3 text-xs">
      <span className={`px-2.5 py-1 rounded-full font-semibold tracking-wide uppercase ${badgeColor}`}>
        {status.status}
      </span>

      {status.clave_acceso && (
        <span className="text-gray-600">
          {country === 'EC' ? t('billing.einvoiceStatus.receipt') : t('billing.einvoiceStatus.ref')}: {' '}
          <span className="font-medium text-gray-800">{status.clave_acceso}</span>
        </span>
      )}

      {status.submitted_at && (
        <span className="text-gray-500">
          {t('billing.einvoiceStatus.submittedAt')}: {new Date(status.submitted_at).toLocaleString()}
        </span>
      )}

      <button
        type="button"
        onClick={loadStatus}
        disabled={loading || sending}
        className="text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label={t('billing.einvoiceStatus.refresh')}
        title={t('billing.einvoiceStatus.refresh') || ''}
      >
        ↻
      </button>

      {canSend && (
        <button
          type="button"
          onClick={handleSend}
          disabled={sending || loading}
          className="text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t('billing.einvoiceStatus.resend')}
        </button>
      )}

      {showError && (
        <span className="text-red-600" title={status.error_message || undefined}>
          ⚠️ {status.error_message || error}
        </span>
      )}
    </div>
  )
}
