/**
 * StoreCreditsList - Vista de gestión de vales/store credits
 * Conecta con: GET /api/v1/pos/store_credits
 */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { listStoreCredits, getStoreCreditByCode } from '../services'
import type { StoreCredit } from '../../../types/pos'
import { useToast } from '../../../shared/toast'

export default function StoreCreditsList() {
  const { t } = useTranslation(['pos', 'common'])
  const toast = useToast()
  const [credits, setCredits] = useState<StoreCredit[]>([])
  const [searchCode, setSearchCode] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadCredits()
  }, [])

  const loadCredits = async () => {
    setLoading(true)
    try {
      const data = await listStoreCredits()
      setCredits(data)
    } catch (error) {
      console.error('Error loading store credits:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchCode.trim()) {
      loadCredits()
      return
    }

    setLoading(true)
    try {
      const credit = await getStoreCreditByCode(searchCode)
      setCredits([credit])
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('pos:storeCredits.notFound'))
      setCredits([])
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      active: 'bg-green-100 text-green-800',
      redeemed: 'bg-gray-100 text-gray-800',
      expired: 'bg-red-100 text-red-800',
      void: 'bg-orange-100 text-orange-800'
    }
    return colors[status as keyof typeof colors] || 'bg-gray-100'
  }

  const getStatusLabel = (status: string) => {
    const labels = {
      active: t('pos:storeCredits.active'),
      redeemed: t('pos:storeCredits.redeemed'),
      expired: t('pos:storeCredits.expired'),
      void: t('pos:storeCredits.voided')
    }
    return labels[status as keyof typeof labels] || status
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">{t('pos:storeCredits.pageTitle')}</h1>

      {/* Búsqueda */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder={t('pos:storeCredits.searchPlaceholder')}
          value={searchCode}
          onChange={(e) => setSearchCode(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          🔍 {t('pos:storeCredits.search')}
        </button>
        <button
          onClick={loadCredits}
          className="px-4 py-2 border rounded hover:bg-gray-50"
        >
          {t('pos:storeCredits.viewAll')}
        </button>
      </div>

      {/* Tabla */}
      {loading ? (
        <p className="text-center py-8 text-gray-500">{t('pos:storeCredits.loading')}</p>
      ) : (
        <div className="overflow-x-auto shadow rounded-lg">
          <table className="w-full border-collapse bg-white">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-3 text-left font-semibold">{t('pos:storeCredits.code')}</th>
                <th className="border p-3 text-left font-semibold">{t('pos:storeCredits.customer')}</th>
                <th className="border p-3 text-right font-semibold">{t('pos:storeCredits.initialAmount')}</th>
                <th className="border p-3 text-right font-semibold">{t('pos:storeCredits.remaining')}</th>
                <th className="border p-3 text-center font-semibold">{t('pos:storeCredits.currency')}</th>
                <th className="border p-3 text-center font-semibold">{t('pos:storeCredits.status')}</th>
                <th className="border p-3 text-left font-semibold">{t('pos:storeCredits.expiration')}</th>
                <th className="border p-3 text-left font-semibold">{t('pos:storeCredits.createdAt')}</th>
              </tr>
            </thead>
            <tbody>
              {credits.length === 0 ? (
                <tr>
                  <td colSpan={8} className="border p-8 text-center text-gray-500">
                    {t('pos:storeCredits.noCredits')}
                  </td>
                </tr>
              ) : (
                credits.map(credit => (
                  <tr key={credit.id} className="hover:bg-gray-50 transition">
                    <td className="border p-3 font-mono text-blue-600 font-semibold">
                      {credit.code}
                    </td>
                    <td className="border p-3">{credit.customer_id || '-'}</td>
                    <td className="border p-3 text-right">{credit.amount_initial.toFixed(2)}</td>
                    <td className="border p-3 text-right font-semibold text-green-700">
                      {credit.amount_remaining.toFixed(2)}
                    </td>
                    <td className="border p-3 text-center">{credit.currency}</td>
                    <td className="border p-3 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${getStatusBadge(credit.status)}`}>
                        {getStatusLabel(credit.status)}
                      </span>
                    </td>
                    <td className="border p-3">
                      {credit.expires_at
                        ? new Date(credit.expires_at).toLocaleDateString()
                        : t('pos:storeCredits.noExpiration')}
                    </td>
                    <td className="border p-3">
                      {new Date(credit.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Resumen */}
      {credits.length > 0 && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-gray-700">
            <strong>{t('pos:storeCredits.totalCredits')}:</strong> {credits.length} |
            <strong className="ml-4">{t('pos:storeCredits.activeCount')}:</strong> {credits.filter(c => c.status === 'active').length} |
            <strong className="ml-4">{t('pos:storeCredits.availableBalance')}:</strong> {' '}
            {credits
              .filter(c => c.status === 'active')
              .reduce((sum, c) => sum + c.amount_remaining, 0)
              .toFixed(2)} {credits[0]?.currency || ''}
          </p>
        </div>
      )}
    </div>
  )
}
