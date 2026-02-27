import React, { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { sendToSii, retryEInvoice, type EInvoice } from './services'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-blue-100 text-blue-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  error: 'bg-red-100 text-red-800',
}

export default function EInvoicingDashboard() {
  const { t } = useTranslation(['einvoicing', 'common'])
  const [invoiceId, setInvoiceId] = useState('')
  const [results, setResults] = useState<EInvoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSend = useCallback(async () => {
    if (!invoiceId.trim()) return
    setLoading(true)
    setError(null)
    try {
      const result = await sendToSii({ invoice_id: invoiceId.trim() })
      setResults((prev) => [result, ...prev])
      setInvoiceId('')
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || t('einvoicing:errorSending'))
    } finally {
      setLoading(false)
    }
  }, [invoiceId])

  const handleRetry = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await retryEInvoice(id)
      setResults((prev) => prev.map((r) => (r.id === id ? result : r)))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || t('einvoicing:errorRetrying'))
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        📄 {t('einvoicing:title')}
      </h1>

      {/* Send form */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">
          {t('einvoicing:sendToSii')}
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
            placeholder={t('einvoicing:invoiceIdPlaceholder')}
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={loading || !invoiceId.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('einvoicing:sending') : t('einvoicing:send')}
          </button>
        </div>
        {error && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Results table */}
      {results.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t('einvoicing:invoice')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t('einvoicing:country')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t('einvoicing:status')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t('einvoicing:date')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t('einvoicing:actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {results.map((inv) => (
                <tr key={inv.id}>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {inv.invoice_number || inv.invoice_id}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {inv.country || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${STATUS_STYLES[inv.status] || 'bg-gray-100 text-gray-800'}`}
                    >
                      {t(`einvoicing:statuses.${inv.status}`, inv.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {inv.submitted_at
                      ? new Date(inv.submitted_at).toLocaleString()
                      : '-'}
                  </td>
                  <td className="px-4 py-3">
                    {(inv.status === 'error' || inv.status === 'rejected') && (
                      <button
                        onClick={() => handleRetry(inv.id)}
                        disabled={loading}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium disabled:opacity-50"
                      >
                        {t('einvoicing:retry')}
                      </button>
                    )}
                    {inv.error_detail && (
                      <span className="ml-2 text-xs text-red-500" title={inv.error_detail}>
                        ⚠️
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {results.length === 0 && (
        <div className="text-center text-gray-500 py-12">
          <div className="text-4xl mb-3">📄</div>
          <p>{t('einvoicing:noSubmissions')}</p>
        </div>
      )}
    </div>
  )
}
